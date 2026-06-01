"""Tests for URL extraction and filtering in both podcast check scripts."""
import os
import sys
import tempfile
import pytest

# Add the repository root to sys.path so we can import the scripts directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from check_active_podcasts import (
    read_podcastindex_urls_from_readme,
    validate_csv as validate_csv_podcasts,
    _parse_date as parse_date_podcasts,
)
from check_active_sites import (
    is_ignored_url,
    extract_urls_from_markdown,
    validate_csv as validate_csv_sites,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_temp_md(content):
    """Write content to a temporary .md file and return its path."""
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
    f.write(content)
    f.close()
    return f.name


def _write_temp_csv(content):
    """Write content to a temporary .csv file and return its path."""
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    f.write(content)
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# read_podcastindex_urls_from_readme
# ---------------------------------------------------------------------------

class TestReadPodcastindexUrls:
    def test_extracts_podcastindex_url(self):
        path = _write_temp_md("Link: <https://podcastindex.org/podcast/12345>")
        try:
            urls = read_podcastindex_urls_from_readme(path)
            assert 'https://podcastindex.org/podcast/12345' in urls
        finally:
            os.unlink(path)

    def test_extracts_multiple_podcastindex_urls(self):
        path = _write_temp_md(
            "First <https://podcastindex.org/podcast/111>\n"
            "Second <https://podcastindex.org/podcast/222>\n"
        )
        try:
            urls = read_podcastindex_urls_from_readme(path)
            assert len(urls) == 2
            assert 'https://podcastindex.org/podcast/111' in urls
            assert 'https://podcastindex.org/podcast/222' in urls
        finally:
            os.unlink(path)

    def test_ignores_non_podcastindex_urls(self):
        path = _write_temp_md("Visit <https://example.com> and <https://otherpodcast.org>")
        try:
            assert read_podcastindex_urls_from_readme(path) == []
        finally:
            os.unlink(path)

    def test_empty_file_returns_empty_list(self):
        path = _write_temp_md("")
        try:
            assert read_podcastindex_urls_from_readme(path) == []
        finally:
            os.unlink(path)

    def test_missing_file_returns_empty_list(self):
        assert read_podcastindex_urls_from_readme('/tmp/nonexistent_xyz_abc.md') == []


# ---------------------------------------------------------------------------
# is_ignored_url
# ---------------------------------------------------------------------------

class TestIsIgnoredUrl:
    def test_twitter_is_ignored(self):
        assert is_ignored_url('https://twitter.com/someuser') is True

    def test_x_com_is_ignored(self):
        assert is_ignored_url('https://x.com/someuser') is True

    def test_infosec_exchange_is_ignored(self):
        assert is_ignored_url('https://infosec.exchange/@user') is True

    def test_mastodon_social_is_ignored(self):
        assert is_ignored_url('https://mastodon.social/@user') is True

    def test_hachyderm_is_ignored(self):
        assert is_ignored_url('https://hachyderm.io/@user') is True

    def test_reddit_is_ignored(self):
        assert is_ignored_url('https://www.reddit.com/r/netsec/') is True

    def test_youtube_at_channel_is_ignored(self):
        assert is_ignored_url('https://www.youtube.com/@SomeChannel') is True

    def test_youtube_c_channel_is_ignored(self):
        assert is_ignored_url('https://www.youtube.com/c/SomeChannel') is True

    def test_youtube_channel_keyword_is_ignored(self):
        assert is_ignored_url('https://www.youtube.com/channel/UC123abc') is True

    def test_youtube_watch_url_is_not_ignored(self):
        assert is_ignored_url('https://www.youtube.com/watch?v=abc123') is False

    def test_podcastindex_is_not_ignored(self):
        assert is_ignored_url('https://podcastindex.org/podcast/12345') is False

    def test_regular_podcast_site_is_not_ignored(self):
        assert is_ignored_url('https://darknetdiaries.com') is False

    def test_apple_podcasts_is_not_ignored(self):
        assert is_ignored_url('https://podcasts.apple.com/us/podcast/risky-business/id216049971') is False


# ---------------------------------------------------------------------------
# extract_urls_from_markdown
# ---------------------------------------------------------------------------

class TestExtractUrlsFromMarkdown:
    def test_extracts_regular_podcast_url(self):
        path = _write_temp_md("Listen at <https://darknetdiaries.com>")
        try:
            urls = extract_urls_from_markdown(path)
            assert 'https://darknetdiaries.com' in urls
        finally:
            os.unlink(path)

    def test_excludes_social_media_urls(self):
        path = _write_temp_md(
            "Website: <https://example-podcast.com>\n"
            "Twitter: <https://twitter.com/podcast>\n"
            "Mastodon: <https://infosec.exchange/@host>\n"
        )
        try:
            urls = extract_urls_from_markdown(path)
            assert 'https://example-podcast.com' in urls
            assert not any('twitter.com' in u for u in urls)
            assert not any('infosec.exchange' in u for u in urls)
        finally:
            os.unlink(path)

    def test_excludes_youtube_channel_urls(self):
        path = _write_temp_md(
            "Podcast: <https://example.com/podcast>\n"
            "YouTube: <https://www.youtube.com/@SomeChannel>\n"
        )
        try:
            urls = extract_urls_from_markdown(path)
            assert 'https://example.com/podcast' in urls
            assert not any('youtube.com/@' in u for u in urls)
        finally:
            os.unlink(path)

    def test_missing_file_returns_empty_list(self):
        assert extract_urls_from_markdown('/tmp/nonexistent_xyz_abc.md') == []

    def test_empty_file_returns_empty_list(self):
        path = _write_temp_md("")
        try:
            assert extract_urls_from_markdown(path) == []
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------

class TestParseDate:
    def test_rfc7231_format(self):
        dt = parse_date_podcasts("Mon, 06 Nov 2023 08:49:37 GMT")
        assert dt is not None
        assert dt.year == 2023
        assert dt.month == 11
        assert dt.day == 6

    def test_iso8601_with_z_suffix(self):
        dt = parse_date_podcasts("2023-11-06T08:49:37Z")
        assert dt is not None
        assert dt.year == 2023
        assert dt.month == 11

    def test_iso8601_without_z(self):
        dt = parse_date_podcasts("2023-11-06T08:49:37")
        assert dt is not None
        assert dt.year == 2023

    def test_invalid_format_returns_none(self):
        assert parse_date_podcasts("not-a-date") is None

    def test_empty_string_returns_none(self):
        assert parse_date_podcasts("") is None


# ---------------------------------------------------------------------------
# validate_csv — check_active_podcasts
# ---------------------------------------------------------------------------

class TestValidateCsvPodcasts:
    def test_valid_csv_passes(self):
        path = _write_temp_csv(
            "Website,Last Checked,Last Updated,Active\n"
            "https://example.com,2024-01-01,2024-01-01,Yes\n"
        )
        try:
            result = validate_csv_podcasts(path, ['Website', 'Last Checked', 'Last Updated', 'Active'])
            assert result is True
        finally:
            os.unlink(path)

    def test_missing_column_raises_value_error(self):
        path = _write_temp_csv("Website,Last Checked\nhttps://example.com,2024-01-01\n")
        try:
            with pytest.raises(ValueError, match="missing columns"):
                validate_csv_podcasts(path, ['Website', 'Last Checked', 'Last Updated', 'Active'])
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# validate_csv — check_active_sites
# ---------------------------------------------------------------------------

class TestValidateCsvSites:
    def test_valid_csv_passes(self):
        path = _write_temp_csv(
            "URL,Last Updated,Active\nhttps://example.com,2024-01-01,Yes\n"
        )
        try:
            result = validate_csv_sites(path, ['URL', 'Last Updated', 'Active'])
            assert result is True
        finally:
            os.unlink(path)

    def test_missing_column_raises_value_error(self):
        path = _write_temp_csv("URL,Last Updated\nhttps://example.com,2024-01-01\n")
        try:
            with pytest.raises(ValueError, match="missing columns"):
                validate_csv_sites(path, ['URL', 'Last Updated', 'Active'])
        finally:
            os.unlink(path)
