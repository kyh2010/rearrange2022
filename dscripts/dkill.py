"""Tool to terminate multi-node (distributed) training."""

import os
import argparse
import glob


def get_argument_parser():
    """Creates the argument parser."""

    # noinspection PyTypeChecker
    parser = argparse.ArgumentParser(
        description="dkill", formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--screen_ids_file",
        required=False,
        type=str,
        default=None,
        help="Path to file generated by dmain.py with IPs and screen ids for nodes running process."
        " If empty, the tool will scan the `~/.allenact` directory for `screen_ids_file`s.",
    )

    parser.add_argument(
        "--ssh_cmd",
        required=False,
        type=str,
        default="ssh {addr}",
        help="SSH command. Useful to utilize a pre-shared key with 'ssh -i mykey.pem ubuntu@{addr}'. ",
    )

    return parser


def get_args():
    """Creates the argument parser and parses any input arguments."""

    parser = get_argument_parser()
    args = parser.parse_args()

    return args


if __name__ == "__main__":
    args = get_args()

    all_files = (
        [args.screen_ids_file]
        if args.screen_ids_file is not None
        else sorted(
            glob.glob(os.path.join(os.path.expanduser("~"), ".allenact", "*.killfile")),
            reverse=True,
        )
    )

    if len(all_files) == 0:
        print(
            f"No tmux_ids_file found under {os.path.join(os.path.expanduser('~'), '.allenact')}"
        )

    for killfile in all_files:
        with open(killfile, "r") as f:
            nodes = [tuple(line[:-1].split(" ")) for line in f.readlines()]

        do_kill = ""
        while do_kill not in ["y", "n"]:
            do_kill = input(
                f"Stopping processes on {nodes} from {killfile}? [y/N] "
            ).lower()
            if do_kill == "":
                do_kill = "n"

        if do_kill == "y":
            for it, node in enumerate(nodes):
                addr, tmux_name = node

                print(f"Killing tmux {tmux_name} on {addr}")

                ssh_command = (
                    f"{args.ssh_cmd.format(addr=addr)} '"
                    f"tmux kill-session -t {tmux_name} ; "
                    f"sleep 1 ; "
                    f"echo Train processes left running: ; "
                    f"ps aux | grep Train- | grep -v grep ; "
                    f"echo ; "
                    f"'"
                )

                # print(f"SSH command {ssh_command}")
                os.system(ssh_command)

            do_delete = ""
            while do_delete not in ["y", "n"]:
                do_delete = input(f"Delete file {killfile}? [y/N] ").lower()
                if do_delete == "":
                    do_delete = "n"

            if do_delete == "y":
                os.system(f"rm {killfile}")
                print(f"Deleted {killfile}")

    print("DONE")