"""
fable_resolution_demo.py — the executable form of the Resolution fable.

The fable (#06) says: "code is what makes the story and the metal true
of the same boat." This script proves it.

For each claim in the seven fables, the script:
  1. Quotes the story (the fable).
  2. Runs the metal (a callable in the substrate).
  3. Reports whether the two agree.

If they agree, the substrate has captured the fable.
If they do not, the substrate has drifted — the bug is in the
resolution, not in the code.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from quilt_seed import run_resolution


def main():
    print("=" * 70)
    print("THE RESOLUTION — the executable proof that metal agrees with story")
    print("=" * 70)
    print()
    print("The fable says: 'Never write a line of code that cannot be told")
    print("as a story, and never tell a story that cannot be run as code.'")
    print("Anything that fails either test is unresolved.")
    print()
    print("Running all canonical claims:")
    print()

    ledger = run_resolution()
    report = ledger.report()
    print(report)
    print()
    summary = ledger.summary()
    print("=" * 70)
    if summary["all_resolved"]:
        print(f"  ALL {summary['n_resolved']} CLAIMS RESOLVED")
        print(f"  canary: {summary['canary']}")
        print()
        print("  The story and the metal agree on all 13 canonical claims.")
        print("  This is the substrate's proof of life.")
        print("  The fable is true of the substrate.")
        print("  The substrate is true of the fable.")
        print()
        print('  "Code is what makes the story and the metal true of the same boat."')
        return 0
    else:
        n = summary["n_unresolved"]
        print(f"  {n} UNRESOLVED CLAIMS — drift detected")
        return 1


if __name__ == "__main__":
    sys.exit(main())
