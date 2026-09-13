import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "downloads" / "asf.json"
PAGES = (
    ROOT / "content" / "en" / "docs" / "download" / "download.md",
    ROOT / "content" / "cn" / "docs" / "download" / "download.md",
)
I18N = (ROOT / "i18n" / "en.yaml", ROOT / "i18n" / "zh-CN.yaml")

# Exact dist state, verified against
# https://downloads.apache.org/hugegraph/<version>/ on 2026-09-13. The data
# file must derive exactly these artifacts; a new release edits both the data
# file and this expectation with a fresh dist listing.
EXPECTED_ARTIFACTS = {
    "1.7.0": {
        "apache-hugegraph-incubating-1.7.0.tar.gz",
        "apache-hugegraph-toolchain-incubating-1.7.0.tar.gz",
        "apache-hugegraph-incubating-1.7.0-src.tar.gz",
        "apache-hugegraph-toolchain-incubating-1.7.0-src.tar.gz",
        "apache-hugegraph-ai-incubating-1.7.0-src.tar.gz",
        "apache-hugegraph-computer-incubating-1.7.0-src.tar.gz",
    },
    "1.5.0": {
        "apache-hugegraph-incubating-1.5.0.tar.gz",
        "apache-hugegraph-toolchain-incubating-1.5.0.tar.gz",
        "apache-hugegraph-incubating-1.5.0-src.tar.gz",
        "apache-hugegraph-toolchain-incubating-1.5.0-src.tar.gz",
        "apache-hugegraph-ai-incubating-1.5.0-src.tar.gz",
        "apache-hugegraph-computer-incubating-1.5.0-src.tar.gz",
    },
    "1.3.0": {
        "apache-hugegraph-incubating-1.3.0.tar.gz",
        "apache-hugegraph-toolchain-incubating-1.3.0.tar.gz",
        "apache-hugegraph-incubating-1.3.0-src.tar.gz",
        "apache-hugegraph-toolchain-incubating-1.3.0-src.tar.gz",
        "apache-hugegraph-ai-incubating-1.3.0-src.tar.gz",
        "apache-hugegraph-commons-incubating-1.3.0-src.tar.gz",
    },
    "1.2.0": {
        "apache-hugegraph-incubating-1.2.0.tar.gz",
        "apache-hugegraph-toolchain-incubating-1.2.0.tar.gz",
        "apache-hugegraph-incubating-1.2.0-src.tar.gz",
        "apache-hugegraph-toolchain-incubating-1.2.0-src.tar.gz",
        "apache-hugegraph-computer-incubating-1.2.0-src.tar.gz",
        "apache-hugegraph-commons-incubating-1.2.0-src.tar.gz",
    },
    "1.0.0": {
        "apache-hugegraph-incubating-1.0.0.tar.gz",
        "apache-hugegraph-toolchain-incubating-1.0.0.tar.gz",
        "apache-hugegraph-computer-incubating-1.0.0.tar.gz",
        "apache-hugegraph-incubating-1.0.0-src.tar.gz",
        "apache-hugegraph-toolchain-incubating-1.0.0-src.tar.gz",
        "apache-hugegraph-computer-incubating-1.0.0-src.tar.gz",
        "apache-hugegraph-commons-incubating-1.0.0-src.tar.gz",
    },
}

FIXED_I18N_KEYS = (
    "download_release_version",
    "download_release_date",
    "download_release_notes",
    "download_table_component",
    "download_table_type",
    "download_table_mirror",
    "download_type_binary",
    "download_type_source",
    "download_asf_note",
)


def load_data() -> dict:
    with DATA.open(encoding="utf-8") as handle:
        return json.load(handle)


def derive_files(release: dict, components: dict) -> set[str]:
    files = set()
    for kind, suffix in (("binary", ""), ("source", "-src")):
        for component_id in release.get(kind, []):
            prefix = components[component_id]["prefix"]
            files.add(f"{prefix}-{release['version']}{suffix}.tar.gz")
    return files


def i18n_keys(path: pathlib.Path) -> set[str]:
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith(("#", " ")) and ":" in line:
            keys.add(line.split(":", 1)[0].strip())
    return keys


class DownloadDataTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = load_data()

    def test_schema_and_release_ordering(self) -> None:
        data = self.data
        self.assertEqual(data["dist_path"], "hugegraph")
        self.assertTrue(data["keys_url"].startswith("https://downloads.apache.org/"))
        for component_id, component in data["components"].items():
            self.assertRegex(component_id, r"^[a-z][a-z0-9]*$")
            self.assertRegex(component["prefix"], r"^apache-hugegraph[a-z-]*-incubating$")
            self.assertRegex(component["label_key"], r"^download_component_[a-z]+$")
        releases = data["releases"]
        versions = [release["version"] for release in releases]
        self.assertEqual(versions, sorted(versions, key=lambda v: tuple(map(int, v.split("."))), reverse=True))
        self.assertEqual(len(versions), len(set(versions)))
        self.assertEqual(sum(1 for release in releases if release.get("latest")), 1)
        self.assertTrue(releases[0].get("latest"), "the newest release must be the latest")
        for release in releases:
            self.assertRegex(release["version"], r"^\d+\.\d+\.\d+$")
            self.assertRegex(release["date"], r"^\d{4}-\d{2}-\d{2}$")
            for kind in ("binary", "source"):
                ids = release.get(kind, [])
                self.assertTrue(ids, f"{release['version']} has no {kind} artifacts")
                self.assertEqual(len(ids), len(set(ids)))
                for component_id in ids:
                    self.assertIn(component_id, data["components"])

    def test_derived_artifacts_match_the_verified_dist_listing(self) -> None:
        data = self.data
        derived = {
            release["version"]: derive_files(release, data["components"])
            for release in data["releases"]
        }
        self.assertEqual(derived, EXPECTED_ARTIFACTS)
        total = sum(len(files) for files in derived.values())
        self.assertEqual(total, 31)

    def test_derived_urls_are_well_formed(self) -> None:
        data = self.data
        pattern = re.compile(r"^https://[a-z.]+/[A-Za-z0-9./?=_-]+$")
        for release in data["releases"]:
            for file in derive_files(release, data["components"]):
                urls = (
                    f"https://www.apache.org/dyn/closer.lua/{data['dist_path']}/"
                    f"{release['version']}/{file}?action=download",
                    f"https://downloads.apache.org/{data['dist_path']}/"
                    f"{release['version']}/{file}.asc",
                    f"https://downloads.apache.org/{data['dist_path']}/"
                    f"{release['version']}/{file}.sha512",
                )
                for url in urls:
                    self.assertRegex(url, pattern)

    def test_pages_render_from_data_not_hardcoded_tables(self) -> None:
        for page in PAGES:
            text = page.read_text(encoding="utf-8")
            self.assertIn("{{< asf-downloads latest >}}", text, page)
            self.assertIn("{{< asf-downloads archived >}}", text, page)
            self.assertNotIn("closer.lua", text, page)
            self.assertNotIn(".tar.gz", text, page)
            artifact_links = re.findall(
                r"downloads\.apache\.org/hugegraph/\d", text
            )
            self.assertEqual(artifact_links, [], page)

    def test_i18n_catalogues_carry_every_label(self) -> None:
        data = self.data
        required = set(FIXED_I18N_KEYS)
        for component in data["components"].values():
            required.add(component["label_key"])
        for catalogue in I18N:
            missing = required - i18n_keys(catalogue)
            self.assertEqual(missing, set(), catalogue)


if __name__ == "__main__":
    unittest.main()
