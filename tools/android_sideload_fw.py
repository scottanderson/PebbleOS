#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Core Devices LLC
# SPDX-License-Identifier: Apache-2.0

"""Sideload a firmware .pbz onto a Pebble via the Android companion app."""

import argparse
import glob
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE_PATH = "/data/local/tmp/firmware.pbz"
ACTION = "coredevices.pebble.SIDELOAD_FIRMWARE"
COMPONENT = "coredevices.coreapp/coredevices.pebble.firmware.FirmwareSideloadReceiver"


def newest_pbz(build_dir, slot):
    matches = glob.glob(os.path.join(REPO_ROOT, build_dir, f"normal_*_slot{slot}.pbz"))
    return max(matches, key=os.path.getmtime) if matches else None


def build_dual_slot(board, slot1_dir):
    """Build both slots and merge them, so the app can update whichever is inactive."""
    if not os.path.isfile(os.path.join(REPO_ROOT, slot1_dir, "build.ninja")):
        subprocess.run(
            ["pbl", "configure", "--board", board, "-b", slot1_dir, "-DCONFIG_FIRMWARE_SLOT=1"],
            check=True,
            cwd=REPO_ROOT,
        )
    for args in ([], ["-b", slot1_dir]):
        subprocess.run(["pbl", "build", *args], check=True, cwd=REPO_ROOT)
        subprocess.run(["pbl", "bundle", *args], check=True, cwd=REPO_ROOT)
    merged = os.path.join(REPO_ROOT, "build", "merged.pbz")
    subprocess.run(
        [
            sys.executable,
            os.path.join(REPO_ROOT, "tools", "merge_pbz.py"),
            "--slot0-pbz", newest_pbz("build", 0),
            "--slot1-pbz", newest_pbz(slot1_dir, 1),
            "--output", merged,
        ],
        check=True,
    )
    return merged


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pbz", nargs="?", help="Path to .pbz (defaults to a fresh dual-slot build)")
    p.add_argument("--board", default="obelix@pvt", help="Board used to configure the slot 1 build")
    p.add_argument("--slot1-dir", default="build-slot1", help="Build directory for slot 1")
    args = p.parse_args()

    pbz = args.pbz or build_dual_slot(args.board, args.slot1_dir)
    if not pbz or not os.path.isfile(pbz):
        sys.exit("no .pbz found — pass one, or run `pbl build` first")

    print(f"sideloading {pbz}")
    subprocess.run(["adb", "push", pbz, REMOTE_PATH], check=True)
    subprocess.run(
        ["adb", "shell", "am", "broadcast",
         "-a", ACTION, "-n", COMPONENT, "--es", "path", REMOTE_PATH],
        check=True,
    )


if __name__ == "__main__":
    main()
