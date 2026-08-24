"""Mutation specs, one module per target.

A spec module declares:
  TARGET        path to the file to mutate, relative to the repo root
  ARGV          argv to run the target's own selftest, e.g. ["selftest"]
  MUTATIONS     list of (name, what_a_regression_here_means, find, replace)

`find` must occur EXACTLY ONCE in the target. The driver reports a pattern that
matches zero or two or more times as UNGUARDED rather than passing over it, since
a mutation that was never applied caught nothing.
"""
