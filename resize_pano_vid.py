#!/usr/bin/env python3

from __future__ import annotations

import platform
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer


app = typer.Typer(
    help="Downscale 2:1 equirectangular video using HEVC and FFmpeg.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


class Resolution(str, Enum):
    """Semantic equirectangular resolutions."""

    ONE_K = "1K"
    TWO_K = "2K"
    FOUR_K = "4K"
    EIGHT_K = "8K"


RESOLUTION_WIDTHS: dict[Resolution, int] = {
    Resolution.ONE_K: 960,
    Resolution.TWO_K: 1920,
    Resolution.FOUR_K: 3840,
    Resolution.EIGHT_K: 7680,
}


@dataclass(frozen=True)
class EncoderConfig:
    name: str
    label: str
    extra_input_args: tuple[str, ...] = ()
    extra_filter_suffix: str = ""
    extra_output_args: tuple[str, ...] = ()


def find_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")

    if ffmpeg is None:
        typer.secho(
            "Error: FFmpeg was not found in PATH.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    return ffmpeg


def available_encoders(ffmpeg: str) -> set[str]:
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-encoders"],
        check=True,
        capture_output=True,
        text=True,
    )

    encoders: set[str] = set()

    for line in result.stdout.splitlines():
        fields = line.split()

        # Typical line:
        # V....D hevc_nvenc  NVIDIA NVENC hevc encoder
        if len(fields) >= 2 and fields[0].startswith("V"):
            encoders.add(fields[1])

    return encoders


def quality_to_quantizer(quality: int) -> int:
    """
    Map user-facing quality 1..10 to a codec quantizer-like value.

    1  -> 35: lower quality, smaller output
    10 -> 17: higher quality, larger output
    """
    return 37 - 2 * quality


def quality_to_videotoolbox(quality: int) -> int:
    """
    Map user-facing quality 1..10 to VideoToolbox's increasing quality scale.

    1  -> 25
    10 -> 95
    """
    return round(25 + (quality - 1) * (70 / 9))


def encoder_candidates(system: str) -> list[EncoderConfig]:
    """
    Return hardware encoders in a platform-appropriate preference order.

    Encoder availability is still checked against the installed FFmpeg build.
    """
    videotoolbox = EncoderConfig(
        name="hevc_videotoolbox",
        label="Apple VideoToolbox",
        extra_output_args=("-allow_sw", "0"),
    )

    nvenc = EncoderConfig(
        name="hevc_nvenc",
        label="NVIDIA NVENC",
    )

    qsv = EncoderConfig(
        name="hevc_qsv",
        label="Intel Quick Sync",
    )

    amf = EncoderConfig(
        name="hevc_amf",
        label="AMD AMF",
    )

    vaapi = EncoderConfig(
        name="hevc_vaapi",
        label="VAAPI",
        extra_input_args=(
            "-vaapi_device",
            "/dev/dri/renderD128",
        ),
        extra_filter_suffix=",format=nv12,hwupload",
    )

    if system == "Darwin":
        return [videotoolbox]

    if system == "Windows":
        return [nvenc, qsv, amf]

    if system == "Linux":
        return [nvenc, qsv, vaapi]

    return [nvenc, qsv, amf, vaapi, videotoolbox]


def encoder_quality_args(encoder: str, quality: int) -> list[str]:
    quantizer = quality_to_quantizer(quality)

    if encoder == "hevc_videotoolbox":
        return [
            "-q:v",
            str(quality_to_videotoolbox(quality)),
            "-realtime",
            "0",
        ]

    if encoder == "hevc_nvenc":
        return [
            "-preset",
            "p6",
            "-tune",
            "hq",
            "-rc",
            "vbr",
            "-cq",
            str(quantizer),
            "-b:v",
            "0",
        ]

    if encoder == "hevc_qsv":
        return [
            "-preset",
            "slow",
            "-global_quality",
            str(quantizer),
        ]

    if encoder == "hevc_amf":
        return [
            "-quality",
            "quality",
            "-rc",
            "cqp",
            "-qp_i",
            str(quantizer),
            "-qp_p",
            str(quantizer),
        ]

    if encoder == "hevc_vaapi":
        return [
            "-rc_mode",
            "CQP",
            "-global_quality",
            str(quantizer),
        ]

    if encoder == "libx265":
        return [
            "-preset",
            "slow",
            "-crf",
            str(quantizer),
            "-x265-params",
            "log-level=error",
        ]

    raise ValueError(f"Unsupported encoder: {encoder}")


def build_video_filter(
    width: int,
    encoder: EncoderConfig,
) -> str:
    height = width // 2

    return (
        f"scale={width}:{height}:flags=lanczos"
        f"{encoder.extra_filter_suffix}"
    )


def probe_encoder(
    *,
    ffmpeg: str,
    input_path: Path,
    width: int,
    quality: int,
    encoder: EncoderConfig,
) -> bool:
    """
    Try encoding one frame from the real input.

    This catches cases where an encoder is present in the FFmpeg build but
    cannot initialize on the current hardware or driver.
    """
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        *encoder.extra_input_args,
        "-hwaccel",
        "auto",
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
        "-frames:v",
        "1",
        "-vf",
        build_video_filter(width, encoder),
        "-c:v",
        encoder.name,
        *encoder_quality_args(encoder.name, quality),
        "-an",
        "-f",
        "null",
        "-",
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    return result.returncode == 0


def choose_encoder(
    *,
    ffmpeg: str,
    input_path: Path,
    width: int,
    quality: int,
    requested_encoder: str,
    hardware_only: bool,
) -> EncoderConfig:
    encoders = available_encoders(ffmpeg)
    system = platform.system()

    if requested_encoder != "auto":
        if requested_encoder not in encoders:
            raise typer.BadParameter(
                f"Encoder '{requested_encoder}' is not included in this "
                "FFmpeg build.",
                param_hint="--encoder",
            )

        candidate = next(
            (
                item
                for item in encoder_candidates(system)
                if item.name == requested_encoder
            ),
            EncoderConfig(
                name=requested_encoder,
                label=requested_encoder,
            ),
        )

        if not probe_encoder(
            ffmpeg=ffmpeg,
            input_path=input_path,
            width=width,
            quality=quality,
            encoder=candidate,
        ):
            typer.secho(
                f"Error: encoder '{requested_encoder}' could not initialize.",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)

        return candidate

    for candidate in encoder_candidates(system):
        if candidate.name not in encoders:
            continue

        typer.echo(f"Testing {candidate.label}...")

        if probe_encoder(
            ffmpeg=ffmpeg,
            input_path=input_path,
            width=width,
            quality=quality,
            encoder=candidate,
        ):
            return candidate

    if hardware_only:
        typer.secho(
            "Error: no usable hardware HEVC encoder was found.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    if "libx265" not in encoders:
        typer.secho(
            "Error: no usable hardware HEVC encoder was found, and this "
            "FFmpeg build does not include libx265.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    typer.secho(
        "Warning: no usable hardware HEVC encoder was found; "
        "falling back to libx265.",
        fg=typer.colors.YELLOW,
        err=True,
    )

    return EncoderConfig(
        name="libx265",
        label="x265 software encoder",
    )


def default_output_path(
    *,
    input_path: Path,
    resolution_label: str,
) -> Path:
    # Preserve common HEVC-capable containers. Otherwise default to MP4.
    supported_suffixes = {".mp4", ".m4v", ".mov", ".mkv"}

    suffix = input_path.suffix.lower()

    if suffix not in supported_suffixes:
        suffix = ".mp4"

    return input_path.with_name(
        f"{input_path.stem}_{resolution_label}{suffix}"
    )


def format_command(command: list[str]) -> str:
    if sys.platform == "win32":
        return subprocess.list2cmdline(command)

    return shlex.join(command)


@app.command()
def main(
    input_path: Annotated[
        Path,
        typer.Argument(
            help="Input equirectangular video.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
    output_path: Annotated[
        Path | None,
        typer.Argument(
            help=(
                "Output path. Defaults to "
                "<input_name>_<resolution>.<ext>."
            ),
            file_okay=True,
            dir_okay=False,
            resolve_path=True,
        ),
    ] = None,
    resolution: Annotated[
        Resolution,
        typer.Option(
            "--resolution",
            "-r",
            case_sensitive=False,
            help="Semantic equirectangular output resolution.",
        ),
    ] = Resolution.TWO_K,
    width: Annotated[
        int | None,
        typer.Option(
            "--width",
            "-w",
            min=2,
            help=(
                "Exact output width. Overrides --resolution. "
                "Height is always width / 2."
            ),
        ),
    ] = None,
    quality: Annotated[
        int,
        typer.Option(
            "--quality",
            "-q",
            min=1,
            max=10,
            help=(
                "Quality from 1 (smallest output) to 10 (highest quality). "
                "8 is recommended."
            ),
        ),
    ] = 8,
    encoder: Annotated[
        str,
        typer.Option(
            "--encoder",
            help=(
                "HEVC encoder name, or 'auto'. Examples: "
                "hevc_videotoolbox, hevc_nvenc, hevc_qsv, "
                "hevc_amf, hevc_vaapi, libx265."
            ),
        ),
    ] = "auto",
    hardware_only: Annotated[
        bool,
        typer.Option(
            "--hardware-only",
            help="Fail instead of falling back to software HEVC encoding.",
        ),
    ] = False,
    audio: Annotated[
        bool,
        typer.Option(
            "--audio/--no-audio",
            help="Copy the input audio stream.",
        ),
    ] = False,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            "-y",
            help="Overwrite an existing output file.",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Print the FFmpeg command without running it.",
        ),
    ] = False,
) -> None:
    """
    Downscale a 2:1 equirectangular video and encode it as HEVC.
    """
    ffmpeg = find_ffmpeg()

    if width is None:
        selected_width = RESOLUTION_WIDTHS[resolution]
        resolution_label = resolution.value
    else:
        selected_width = width
        resolution_label = f"{width}w"

    if selected_width % 2 != 0:
        raise typer.BadParameter(
            "Width must be even so that width / 2 is an integer.",
            param_hint="--width",
        )

    selected_height = selected_width // 2

    if output_path is None:
        output_path = default_output_path(
            input_path=input_path,
            resolution_label=resolution_label,
        )

    if input_path == output_path:
        raise typer.BadParameter(
            "Input and output paths must be different.",
            param_hint="OUTPUT_PATH",
        )

    if output_path.exists() and not overwrite:
        typer.secho(
            f"Error: output already exists: {output_path}",
            fg=typer.colors.RED,
            err=True,
        )
        typer.echo("Use --overwrite to replace it.", err=True)
        raise typer.Exit(code=1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    selected_encoder = choose_encoder(
        ffmpeg=ffmpeg,
        input_path=input_path,
        width=selected_width,
        quality=quality,
        requested_encoder=encoder.lower(),
        hardware_only=hardware_only,
    )

    typer.secho(
        f"Encoder: {selected_encoder.label}",
        fg=typer.colors.CYAN,
    )
    typer.echo(
        f"Resolution: {selected_width}x{selected_height} "
        f"({resolution_label})"
    )
    typer.echo(f"Quality: {quality}/10")

    command = [
        ffmpeg,
        "-hide_banner",
        *selected_encoder.extra_input_args,
        "-hwaccel",
        "auto",
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
        "-vf",
        build_video_filter(selected_width, selected_encoder),
        "-c:v",
        selected_encoder.name,
        *encoder_quality_args(selected_encoder.name, quality),
        "-pix_fmt",
        "yuv420p",
    ]

    # hvc1 improves HEVC compatibility in Apple-oriented MP4/MOV workflows.
    if output_path.suffix.lower() in {".mp4", ".m4v", ".mov"}:
        command.extend(["-tag:v", "hvc1"])
        command.extend(["-movflags", "+faststart"])

    if audio:
        command.extend(
            [
                "-map",
                "0:a?",
                "-c:a",
                "copy",
            ]
        )
    else:
        command.append("-an")

    command.extend(
        [
            "-y" if overwrite else "-n",
            str(output_path),
        ]
    )

    typer.echo("\nFFmpeg command:")
    typer.echo(format_command(command))

    if dry_run:
        return

    try:
        subprocess.run(
            command,
            check=True,
            shell=False,
        )
    except subprocess.CalledProcessError as exc:
        typer.secho(
            f"FFmpeg failed with exit code {exc.returncode}.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=exc.returncode) from exc
    except KeyboardInterrupt:
        typer.secho(
            "\nEncoding interrupted.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        raise typer.Exit(code=130)

    typer.secho(
        f"\nCreated: {output_path}",
        fg=typer.colors.GREEN,
    )


if __name__ == "__main__":
    app()
