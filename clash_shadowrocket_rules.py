#!/usr/bin/env python3
"""Convert the common rule subset between Clash/Mihomo and Shadowrocket.

The converter intentionally handles rules only, not proxy node definitions.
It preserves rule order, policy names, comments, and rule options such as
``no-resolve``. Unsupported rule types fail loudly instead of being silently
changed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


COMMON_RULE_TYPES = {
    "DOMAIN",
    "DOMAIN-SUFFIX",
    "DOMAIN-KEYWORD",
    "IP-CIDR",
    "IP-CIDR6",
    "GEOIP",
}


def auto_convert() -> Path:
    """Convert the only YAML/CONF file next to this script."""
    directory = Path(__file__).resolve().parent
    candidates = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in {".yaml", ".yml", ".conf"}
    )

    if len(candidates) != 1:
        names = ", ".join(path.name for path in candidates) or "没有"
        raise ValueError(
            "请确保脚本所在目录恰好只有一个 .yaml、.yml 或 .conf 文件；"
            f"当前找到：{names}"
        )

    source = candidates[0]
    text = source.read_text(encoding="utf-8")

    if source.suffix.lower() in {".yaml", ".yml"}:
        target = source.with_suffix(".conf")
        items = extract_clash_items(text)
        result = render_shadowrocket(
            convert_items(items, "clash-to-shadowrocket", {})
        )
    else:
        target = source.with_suffix(".yaml")
        items = extract_shadowrocket_items(text)
        result = render_clash(
            convert_items(items, "shadowrocket-to-clash", {})
        )

    if target.exists():
        raise ValueError(f"目标文件已存在，未覆盖：{target.name}")

    target.write_text(result, encoding="utf-8")
    print(f"转换完成：{source.name} -> {target.name}")
    return target


def read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def write_text(path: str | None, content: str) -> None:
    if path:
        Path(path).write_text(content, encoding="utf-8")
    else:
        sys.stdout.write(content)


def decode_yaml_scalar(value: str) -> str:
    """Decode the plain/single-quoted/JSON-quoted scalar forms used for rules."""
    value = value.strip()
    if not value:
        raise ValueError("empty Clash rule")

    if value.startswith('"'):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError(f"unsupported quoted YAML rule: {value}") from error
        if not isinstance(decoded, str):
            raise ValueError(f"Clash rule must be a string: {value}")
        return decoded

    if value.startswith("'"):
        if not value.endswith("'"):
            raise ValueError(f"unterminated YAML rule: {value}")
        return value[1:-1].replace("''", "'")

    # A space followed by # starts an inline YAML comment. Rule values in the
    # supported subset do not otherwise contain this sequence.
    return value.split(" #", 1)[0].rstrip()


def extract_clash_items(text: str) -> list[tuple[str, str]]:
    """Return (kind, value) entries from a Clash rules block or plain rule list."""
    lines = text.splitlines()
    header_index = None
    header_indent = 0

    for index, line in enumerate(lines):
        match = re.match(r"^(\s*)rules\s*:\s*(?:#.*)?$", line)
        if match:
            header_index = index
            header_indent = len(match.group(1))
            break

    if header_index is None:
        return extract_plain_items(lines, "Clash")

    items: list[tuple[str, str]] = []
    for line in lines[header_index + 1 :]:
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        if stripped and indent <= header_indent:
            break
        if not stripped:
            items.append(("blank", ""))
        elif stripped.startswith("#"):
            items.append(("comment", stripped[1:].lstrip()))
        else:
            match = re.match(r"^\s*-\s*(.+?)\s*$", line)
            if not match:
                raise ValueError(f"invalid Clash rule-list line: {line}")
            items.append(("rule", decode_yaml_scalar(match.group(1))))

    if not any(kind == "rule" for kind, _ in items):
        raise ValueError("the Clash rules block contains no rules")
    return trim_blank_items(items)


def extract_shadowrocket_items(text: str) -> list[tuple[str, str]]:
    """Return (kind, value) entries from [Rule] or a plain rule list."""
    lines = text.splitlines()
    section_index = None

    for index, line in enumerate(lines):
        if line.strip().lower() == "[rule]":
            section_index = index
            break

    if section_index is None:
        return extract_plain_items(lines, "Shadowrocket")

    items: list[tuple[str, str]] = []
    for line in lines[section_index + 1 :]:
        stripped = line.strip()
        if re.match(r"^\[[^\]]+\]$", stripped):
            break
        items.append(classify_plain_line(stripped))

    if not any(kind == "rule" for kind, _ in items):
        raise ValueError("the Shadowrocket [Rule] section contains no rules")
    return trim_blank_items(items)


def extract_plain_items(lines: list[str], source: str) -> list[tuple[str, str]]:
    items = [classify_plain_line(line.strip()) for line in lines]
    if not any(kind == "rule" for kind, _ in items):
        raise ValueError(f"the {source} input contains no rules")
    return trim_blank_items(items)


def classify_plain_line(stripped: str) -> tuple[str, str]:
    if not stripped:
        return ("blank", "")
    if stripped.startswith(("#", ";", "//")):
        return ("comment", stripped.lstrip("#;/").lstrip())
    return ("rule", stripped)


def trim_blank_items(items: list[tuple[str, str]]) -> list[tuple[str, str]]:
    while items and items[0][0] == "blank":
        items.pop(0)
    while items and items[-1][0] == "blank":
        items.pop()
    return items


def parse_policy_maps(values: list[str]) -> dict[str, str]:
    mappings: dict[str, str] = {}
    for value in values:
        old, separator, new = value.partition("=")
        if not separator or not old.strip() or not new.strip():
            raise ValueError(f"invalid policy mapping {value!r}; expected OLD=NEW")
        mappings[old.strip()] = new.strip()
    return mappings


def convert_rule(
    rule: str,
    direction: str,
    policy_maps: dict[str, str],
) -> str:
    fields = [field.strip() for field in rule.split(",")]
    rule_type = fields[0].upper()

    if direction == "clash-to-shadowrocket":
        final_from, final_to = "MATCH", "FINAL"
    else:
        final_from, final_to = "FINAL", "MATCH"

    if rule_type == final_from:
        if len(fields) != 2:
            raise ValueError(f"{rule_type} expects exactly one policy: {rule}")
        fields[0] = final_to
        policy_index = 1
    elif rule_type in COMMON_RULE_TYPES:
        if len(fields) < 3:
            raise ValueError(f"{rule_type} rule is missing fields: {rule}")
        policy_index = 2
    else:
        raise ValueError(
            f"unsupported {direction} rule type {rule_type!r}: {rule}"
        )

    fields[policy_index] = policy_maps.get(
        fields[policy_index],
        fields[policy_index],
    )
    return ",".join(fields)


def convert_items(
    items: list[tuple[str, str]],
    direction: str,
    policy_maps: dict[str, str],
) -> list[tuple[str, str]]:
    return [
        (
            kind,
            convert_rule(value, direction, policy_maps)
            if kind == "rule"
            else value,
        )
        for kind, value in items
    ]


def render_shadowrocket(items: list[tuple[str, str]]) -> str:
    lines = ["[Rule]"]
    for kind, value in items:
        if kind == "rule":
            lines.append(value)
        elif kind == "comment":
            lines.append(f"# {value}" if value else "#")
        else:
            lines.append("")
    return "\n".join(lines) + "\n"


def render_clash(items: list[tuple[str, str]]) -> str:
    lines = ["rules:"]
    for kind, value in items:
        if kind == "rule":
            # JSON strings are valid YAML scalars and safely preserve Unicode,
            # commas, quotes, and policy names containing punctuation.
            lines.append(f"  - {json.dumps(value, ensure_ascii=False)}")
        elif kind == "comment":
            lines.append(f"  # {value}" if value else "  #")
        else:
            lines.append("")
    return "\n".join(lines) + "\n"


def run_self_test() -> None:
    source = """\
rules:
  # Domain rules first
  - DOMAIN-SUFFIX,openai.com,🌏 东南节点
  - DOMAIN-KEYWORD,google,🇺🇸 美国节点
  - IP-CIDR,10.0.0.0/8,DIRECT,no-resolve
  - GEOIP,CN,DIRECT
  - MATCH,🌏 东南节点
"""
    original = extract_clash_items(source)
    shadowrocket = render_shadowrocket(
        convert_items(original, "clash-to-shadowrocket", {})
    )
    assert "FINAL,🌏 东南节点" in shadowrocket
    assert "IP-CIDR,10.0.0.0/8,DIRECT,no-resolve" in shadowrocket

    round_trip = convert_items(
        extract_shadowrocket_items(shadowrocket),
        "shadowrocket-to-clash",
        {},
    )
    assert round_trip == original

    renamed = convert_items(
        original,
        "clash-to-shadowrocket",
        {"🌏 东南节点": "SEA"},
    )
    assert any(value == "FINAL,SEA" for kind, value in renamed if kind == "rule")
    print("self-test: ok")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert rules between Clash/Mihomo YAML and Shadowrocket config. "
            "Use '-' or omit INPUT to read stdin."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("clash-to-shadowrocket", "shadowrocket-to-clash"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("input", nargs="?", default="-")
        subparser.add_argument("-o", "--output")
        subparser.add_argument(
            "--map",
            action="append",
            default=[],
            metavar="OLD=NEW",
            help="rename a policy/group; may be repeated",
        )

    subparsers.add_parser("self-test")
    return parser


def main() -> int:
    if len(sys.argv) == 1:
        try:
            auto_convert()
        except (OSError, ValueError) as error:
            print(f"转换失败：{error}", file=sys.stderr)
            return 2
        return 0

    args = build_parser().parse_args()
    if args.command == "self-test":
        run_self_test()
        return 0

    try:
        mappings = parse_policy_maps(args.map)
        text = read_text(args.input)
        if args.command == "clash-to-shadowrocket":
            items = extract_clash_items(text)
            result = render_shadowrocket(
                convert_items(items, args.command, mappings)
            )
        else:
            items = extract_shadowrocket_items(text)
            result = render_clash(convert_items(items, args.command, mappings))
        write_text(args.output, result)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
