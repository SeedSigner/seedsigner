#!/usr/bin/env python

import argparse
import logging
import sys

from seedsigner.controller import Controller

logger = logging.getLogger(__name__)


def main(sys_argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l",
        "--loglevel",
        choices=list((logging._nameToLevel.keys())),
        default="INFO",
        type=str,
        help='Set the log level (default: %(default)s)',
    )

    args = parser.parse_args(sys_argv)
    logging.basicConfig(
        level=logging.getLevelName(args.loglevel),
        format="%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info(f"Starting Seedsigner with: {args.__dict__}")

    # Get the one and only Controller instance and start our main loop
    Controller.get_instance().start()


if __name__ == "__main__":
    main(sys.argv[1:])
