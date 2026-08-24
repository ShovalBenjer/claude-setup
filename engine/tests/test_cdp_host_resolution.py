"""The CDP client must not drive a browser nobody asked for.

Measured on this machine 2026-07-27: two unrelated Chrome instances were both
listening on port 9224, one on 127.0.0.1 with a throwaway profile under Temp and
one on [::1] with the automation profile. IPv4 and IPv6 loopback are separate
sockets, so neither reported a conflict, and `/json/version` on the hardcoded
127.0.0.1 returned a perfectly valid payload from the wrong browser.

That is why these tests are about IDENTITY and not about reachability. An
endpoint answering proves a browser is there; it proves nothing about which one.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "browser"))
import cdp  # noqa: E402


OURS = 4242
STRANGER = 9999


class TestParseListeners:
    def test_maps_address_to_owning_pid_and_strips_ipv6_brackets(self):
        text = "127.0.0.1 9224 19604\n::1 9224 10396\n"
        assert cdp.parse_listeners(text, 9224) == {"127.0.0.1": 19604, "::1": 10396}

    def test_ignores_other_ports(self):
        text = "127.0.0.1 9222 111\n::1 9224 222\n"
        assert cdp.parse_listeners(text, 9224) == {"::1": 222}

    def test_survives_headers_and_blank_lines(self):
        text = "\nLocalAddress LocalPort OwningProcess\n\n::1 9224 10396\n"
        assert cdp.parse_listeners(text, 9224) == {"::1": 10396}


class TestParseProfilePids:
    def test_selects_only_command_lines_naming_the_profile(self):
        text = (
            "10396\tchrome.exe --remote-debugging-port=9224 "
            "--user-data-dir=C:\\Users\\shova\\.claude\\automation-chrome-profile\n"
            "19604\tchrome.exe --remote-debugging-port=9224 "
            "--user-data-dir=C:\\Users\\shova\\AppData\\Local\\Temp\\cdp-prof-v2tree\n"
        )
        assert cdp.parse_profile_pids(text, "automation-chrome-profile") == {10396}

    def test_no_match_is_empty_not_everything(self):
        assert cdp.parse_profile_pids("1\tchrome.exe --foo\n", "automation-chrome-profile") == set()


class TestChooseHost:
    def test_picks_the_address_whose_socket_our_process_owns(self):
        host, why = cdp.choose_host(
            answered={"127.0.0.1": False, "[::1]": True},
            listeners={"::1": OURS},
            profile_pids={OURS},
        )
        assert host == "[::1]"
        assert "verified" in why

    def test_the_live_defect_rejects_the_stranger_and_takes_ours(self):
        """Both answer on the same port. Only one is our profile."""
        host, why = cdp.choose_host(
            answered={"127.0.0.1": True, "[::1]": True},
            listeners={"127.0.0.1": STRANGER, "::1": OURS},
            profile_pids={OURS},
        )
        assert host == "[::1]"
        assert "WARNING" in why
        assert "127.0.0.1" in why

    def test_an_answering_stranger_alone_is_refused_not_adopted(self):
        """The whole point: reachable is not the same as ours."""
        host, why = cdp.choose_host(
            answered={"127.0.0.1": True, "[::1]": False},
            listeners={"127.0.0.1": STRANGER},
            profile_pids={OURS},
        )
        assert host is None
        assert "not this profile" in why

    def test_nothing_listening_reports_both_addresses_tried(self):
        host, why = cdp.choose_host(answered={}, listeners={}, profile_pids=set())
        assert host is None
        assert "127.0.0.1" in why and "[::1]" in why

    def test_without_a_listener_table_it_falls_back_but_says_so(self):
        """Non-Windows or a failed query. Guessing silently is the bug."""
        host, why = cdp.choose_host(
            answered={"127.0.0.1": True}, listeners={}, profile_pids=set())
        assert host == "127.0.0.1"
        assert "UNVERIFIED" in why


class TestWebSocketUrlParsing:
    """The websocket layer must accept the URL the HTTP layer now hands it.

    Resolving to [::1] made /json/version return ws://[::1]:9224/devtools/...
    and `hostport.partition(":")` split that into host='[' and port=':1]:9224'.
    The IPv6 fix in the HTTP layer therefore broke every websocket command, which
    is the whole eval/text/shot surface. Fixing reachability at one layer and
    leaving the next layer IPv4-shaped is half a fix.
    """

    @pytest.mark.parametrize("url,host,port", [
        ("ws://[::1]:9224/devtools/browser/abc", "::1", 9224),
        ("ws://127.0.0.1:9224/devtools/browser/abc", "127.0.0.1", 9224),
        ("ws://localhost:9222/devtools/page/xyz", "localhost", 9222),
        ("ws://[fe80::1%25eth0]:9224/devtools/browser/abc", "fe80::1%25eth0", 9224),
    ])
    def test_split_handles_both_stacks(self, url, host, port):
        assert cdp.split_ws_url(url)[:2] == (host, port)

    def test_path_survives_the_split(self):
        _, _, path = cdp.split_ws_url("ws://[::1]:9224/devtools/browser/abc")
        assert path == "devtools/browser/abc"

    def test_the_host_header_keeps_ipv6_brackets(self):
        """Split for the socket, bracketed for the HTTP Host header."""
        assert cdp.ws_host_header("::1", 9224) == "[::1]:9224"
        assert cdp.ws_host_header("127.0.0.1", 9224) == "127.0.0.1:9224"


class TestEndpointHonoursTheChosenHost:
    def test_url_is_built_from_the_host_argument(self, monkeypatch):
        seen = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b'{"Browser":"x"}'

        def fake_urlopen(url, timeout=None):
            seen["url"] = url
            return FakeResponse()

        monkeypatch.setattr(cdp.urllib.request, "urlopen", fake_urlopen)
        cdp._endpoint("/json/version", host="[::1]")
        assert seen["url"] == "http://[::1]:{}/json/version".format(cdp.PORT)

    def test_no_ipv4_literal_is_left_hardcoded_in_the_http_layer(self):
        """A resolver is worthless if a second call site still pins the stack."""
        src = Path(cdp.__file__).read_text(encoding="utf-8")
        code = [ln for ln in src.splitlines()
                if "127.0.0.1" in ln and not ln.strip().startswith("#")]
        offenders = [ln for ln in code if "http://" in ln]
        assert offenders == [], offenders


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
