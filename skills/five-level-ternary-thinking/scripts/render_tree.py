#!/usr/bin/env python3
"""Validate a five-level ternary reasoning tree and render an HTML fragment."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from typing import Any


MAX_DEPTH = 5
EXPECTED_NODE_COUNT = 364
VALID_MODES = {"what", "why", "how", "mixed"}
MAX_LABEL_LENGTH = 160
MAX_DETAIL_LENGTH = 600
MAX_EXAMPLE_LENGTH = 400


class TreeValidationError(ValueError):
    """Raised when the input does not satisfy the model contract."""


def normalize_label(label: str) -> str:
    return re.sub(r"[\s\W_]+", "", label, flags=re.UNICODE).lower()


def validate_text_field(
    node: dict[str, Any],
    field: str,
    path: str,
    max_length: int,
) -> str:
    value = node.get(field)
    if not isinstance(value, str) or not value.strip():
        raise TreeValidationError(f"{path}: {field} must be a non-empty string")
    value = value.strip()
    if len(value) > max_length:
        raise TreeValidationError(
            f"{path}: {field} is longer than {max_length} characters"
        )
    return value


def validate_node(node: Any, depth: int, path: str) -> int:
    if not isinstance(node, dict):
        raise TreeValidationError(f"{path}: node must be an object")

    label = validate_text_field(node, "label", path, MAX_LABEL_LENGTH)
    detail = validate_text_field(node, "detail", path, MAX_DETAIL_LENGTH)
    example = validate_text_field(node, "example", path, MAX_EXAMPLE_LENGTH)
    if normalize_label(detail) == normalize_label(label):
        raise TreeValidationError(f"{path}: detail must add information beyond label")
    if normalize_label(example) == normalize_label(label):
        raise TreeValidationError(f"{path}: example must not repeat label verbatim")

    node_mode = node.get("mode")
    if node_mode is not None and node_mode not in VALID_MODES:
        raise TreeValidationError(f"{path}: unsupported node mode {node_mode!r}")

    children = node.get("children", [])
    if not isinstance(children, list):
        raise TreeValidationError(f"{path}: children must be an array")

    expected_children = 0 if depth == MAX_DEPTH else 3
    if len(children) != expected_children:
        raise TreeValidationError(
            f"{path}: level {depth} requires {expected_children} children, "
            f"found {len(children)}"
        )

    if children:
        if not all(isinstance(child, dict) for child in children):
            raise TreeValidationError(f"{path}: every child must be an object")
        normalized = [normalize_label(str(child.get("label", ""))) for child in children]
        if len(set(normalized)) != 3:
            raise TreeValidationError(f"{path}: sibling labels must be distinct")

    count = 1
    for index, child in enumerate(children, start=1):
        count += validate_node(child, depth + 1, f"{path}.{index}")
    return count


def assign_node_ids(node: dict[str, Any], indices: tuple[int, ...] = ()) -> None:
    node["id"] = "0" if not indices else ".".join(str(index) for index in indices)
    for index, child in enumerate(node["children"], start=1):
        assign_node_ids(child, (*indices, index))


def load_and_validate(input_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TreeValidationError(f"Input file does not exist: {input_path}") from exc
    except json.JSONDecodeError as exc:
        raise TreeValidationError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise TreeValidationError("Top-level input must be an object")

    mode = data.get("mode")
    if mode not in VALID_MODES:
        raise TreeValidationError(
            f"mode must be one of {sorted(VALID_MODES)}, found {mode!r}"
        )

    root = data.get("root")
    count = validate_node(root, 0, "root")
    if count != EXPECTED_NODE_COUNT:
        raise TreeValidationError(
            f"Tree must contain {EXPECTED_NODE_COUNT} nodes, found {count}"
        )

    assign_node_ids(root)

    title = data.get("title")
    if title is not None and (not isinstance(title, str) or not title.strip()):
        raise TreeValidationError("title must be a non-empty string when provided")

    return data


def render_fragment(data: dict[str, Any]) -> str:
    title = data.get("title") or data["root"]["label"]
    digest = hashlib.sha256(
        (title + data["root"]["label"]).encode("utf-8")
    ).hexdigest()[:10]
    widget_id = f"five-level-ternary-{digest}"

    data_json = json.dumps(
        data,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    data_json = (
        data_json.replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )

    template = r'''<div id="__WIDGET_ID__" role="region" aria-label="__ARIA_LABEL__">
  <div class="viz-controls">
    <span class="viz-badge" data-role="mode">五层三叉</span>
    <span class="viz-badge" data-role="depth">第 0 / 5 层</span>
    <span class="text-muted" data-role="count">完整结构：364 个节点</span>
    <button type="button" class="btn" data-role="back" disabled>返回上一层</button>
    <button type="button" class="btn btn-ghost" data-role="home" disabled>回到根问题</button>
    <button type="button" class="btn btn-ghost" data-role="copy">复制节点引用</button>
  </div>

  <nav class="flt-path" data-role="path" aria-label="当前思考路径"></nav>

  <div class="flt-stage">
    <div class="flt-focus-wrap">
      <div class="card" aria-live="polite">
        <div class="flt-focus-heading">
          <div class="text-small flt-focus-label" data-role="focus-label">节点 0 · 根问题</div>
          <span class="flt-node-id" data-role="focus-id">0</span>
        </div>
        <div class="flt-focus-text" data-role="focus-text"></div>
        <div class="flt-detail-block">
          <div class="text-small flt-section-label">详细解释</div>
          <div class="flt-detail-text" data-role="focus-detail"></div>
        </div>
        <div class="flt-example-block">
          <div class="text-small flt-section-label">通用例子</div>
          <div class="flt-example-text" data-role="focus-example"></div>
        </div>
      </div>
    </div>

    <div class="flt-connectors" data-role="connectors" aria-hidden="true">
      <div class="flt-stem"></div>
      <div class="flt-bar"></div>
      <div class="flt-drops"><span></span><span></span><span></span></div>
    </div>

    <p class="text-small flt-prompt" data-role="prompt"></p>
    <div class="flt-branches" data-role="branches" aria-label="三个子节点"></div>
    <p class="text-small flt-terminal" data-role="terminal" hidden>已经到达第五层。返回上方路径可以继续探索其他分支。</p>
    <p class="text-small flt-reference-hint">与 AI 沟通时可以直接说：“请解释节点 2.1.3”。</p>
  </div>
</div>

<style>
  #__WIDGET_ID__ {
    width: 100%;
    color: var(--foreground, #172033);
    background: var(--background, #ffffff);
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    line-height: 1.6;
  }

  #__WIDGET_ID__,
  #__WIDGET_ID__ * {
    box-sizing: border-box;
  }

  #__WIDGET_ID__ .viz-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
  }

  #__WIDGET_ID__ .viz-badge,
  #__WIDGET_ID__ .flt-node-id {
    display: inline-flex;
    align-items: center;
    border: 1px solid var(--border, #d7deea);
    border-radius: 999px;
    padding: 0.15rem 0.55rem;
    color: var(--foreground, #172033);
    background: var(--muted, #f2f5f9);
    font-size: 0.78rem;
    font-weight: 650;
  }

  #__WIDGET_ID__ .text-muted,
  #__WIDGET_ID__ .text-small {
    color: var(--muted-foreground, #5f6b7d);
    font-size: 0.84rem;
  }

  #__WIDGET_ID__ .btn {
    appearance: none;
    border: 1px solid var(--border, #cfd7e5);
    border-radius: 0.65rem;
    padding: 0.55rem 0.75rem;
    color: var(--foreground, #172033);
    background: var(--card, #ffffff);
    font: inherit;
    line-height: 1.4;
    cursor: pointer;
    white-space: normal;
    overflow-wrap: anywhere;
  }

  #__WIDGET_ID__ .btn:hover:not(:disabled),
  #__WIDGET_ID__ .btn:focus-visible {
    border-color: var(--primary, #315ecf);
    outline: 2px solid color-mix(in srgb, var(--primary, #315ecf) 22%, transparent);
    outline-offset: 1px;
  }

  #__WIDGET_ID__ .btn:disabled {
    cursor: not-allowed;
    opacity: 0.45;
  }

  #__WIDGET_ID__ .btn-block {
    width: 100%;
    min-height: 5rem;
    text-align: left;
  }

  #__WIDGET_ID__ .card {
    border: 1px solid var(--border, #d7deea);
    border-radius: 1rem;
    padding: 1rem 1.1rem;
    color: var(--card-foreground, #172033);
    background: var(--card, #ffffff);
    box-shadow: 0 8px 24px rgba(30, 52, 86, 0.08);
  }

  #__WIDGET_ID__ .flt-path {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.375rem;
    margin: 0.75rem 0;
  }

  #__WIDGET_ID__ .flt-separator {
    color: var(--muted-foreground, #5f6b7d);
  }

  #__WIDGET_ID__ .flt-stage {
    padding: 0.25rem 0 0.5rem;
  }

  #__WIDGET_ID__ .flt-focus-wrap {
    max-width: 52rem;
    margin: 0 auto;
  }

  #__WIDGET_ID__ .flt-focus-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.4rem;
  }

  #__WIDGET_ID__ .flt-focus-label {
    color: var(--card-foreground, #172033);
    opacity: 0.72;
    margin-bottom: 0.375rem;
  }

  #__WIDGET_ID__ .flt-focus-text {
    color: var(--card-foreground, #172033);
    font-size: 1.08rem;
    font-weight: 700;
    line-height: 1.5;
    overflow-wrap: anywhere;
  }

  #__WIDGET_ID__ .flt-detail-block,
  #__WIDGET_ID__ .flt-example-block {
    margin-top: 0.9rem;
    padding-top: 0.8rem;
    border-top: 1px solid var(--border, #e0e5ee);
  }

  #__WIDGET_ID__ .flt-example-block {
    border: 1px solid color-mix(in srgb, var(--primary, #315ecf) 22%, transparent);
    border-radius: 0.75rem;
    padding: 0.75rem 0.85rem;
    background: color-mix(in srgb, var(--primary, #315ecf) 6%, var(--card, #ffffff));
  }

  #__WIDGET_ID__ .flt-section-label {
    margin-bottom: 0.25rem;
    font-weight: 700;
  }

  #__WIDGET_ID__ .flt-detail-text,
  #__WIDGET_ID__ .flt-example-text {
    color: var(--card-foreground, #172033);
    overflow-wrap: anywhere;
  }

  #__WIDGET_ID__ .flt-connectors {
    width: 100%;
  }

  #__WIDGET_ID__ .flt-stem {
    width: 1px;
    height: 1.25rem;
    margin: 0 auto;
    background: var(--border, #d7deea);
  }

  #__WIDGET_ID__ .flt-bar {
    height: 1px;
    margin: 0 16.666%;
    background: var(--border, #d7deea);
  }

  #__WIDGET_ID__ .flt-drops {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  #__WIDGET_ID__ .flt-drops span {
    width: 1px;
    height: 1rem;
    margin: 0 auto;
    background: var(--border, #d7deea);
  }

  #__WIDGET_ID__ .flt-prompt,
  #__WIDGET_ID__ .flt-terminal,
  #__WIDGET_ID__ .flt-reference-hint {
    color: var(--muted-foreground, #5f6b7d);
    text-align: center;
    margin: 0 0 0.75rem;
  }

  #__WIDGET_ID__ .flt-branches {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.75rem;
    align-items: stretch;
  }

  #__WIDGET_ID__ .flt-terminal {
    margin-top: 0.75rem;
  }

  #__WIDGET_ID__ .flt-reference-hint {
    margin-top: 0.9rem;
  }

  #__WIDGET_ID__ .flt-branch-id {
    display: block;
    margin-bottom: 0.35rem;
    color: var(--primary, #315ecf);
    font-size: 0.78rem;
    font-weight: 750;
  }

  #__WIDGET_ID__ .flt-branch-label {
    display: block;
  }

  @media (max-width: 620px) {
    #__WIDGET_ID__ .flt-connectors {
      display: none;
    }

    #__WIDGET_ID__ .flt-prompt {
      margin-top: 0.75rem;
    }

    #__WIDGET_ID__ .flt-branches {
      grid-template-columns: 1fr;
      border-left: 1px solid var(--border, #d7deea);
      padding-left: 0.75rem;
    }

    #__WIDGET_ID__ .flt-focus-heading {
      align-items: flex-start;
    }
  }
</style>

<script>
(() => {
  const data = __DATA_JSON__;
  const rootElement = document.getElementById("__WIDGET_ID__");
  if (!rootElement) return;

  const modeLabels = {
    what: "是什么",
    why: "为什么",
    how: "怎么办",
    mixed: "综合三问"
  };

  const prompts = {
    what: "继续拆解：这个节点还包含什么？",
    why: "继续追问：为什么会出现这个原因？",
    how: "继续细化：这一步具体怎么办？",
    mixed: "继续展开当前思考分支"
  };

  const depthElement = rootElement.querySelector('[data-role="depth"]');
  const modeElement = rootElement.querySelector('[data-role="mode"]');
  const countElement = rootElement.querySelector('[data-role="count"]');
  const backButton = rootElement.querySelector('[data-role="back"]');
  const homeButton = rootElement.querySelector('[data-role="home"]');
  const copyButton = rootElement.querySelector('[data-role="copy"]');
  const pathElement = rootElement.querySelector('[data-role="path"]');
  const focusLabelElement = rootElement.querySelector('[data-role="focus-label"]');
  const focusIdElement = rootElement.querySelector('[data-role="focus-id"]');
  const focusTextElement = rootElement.querySelector('[data-role="focus-text"]');
  const focusDetailElement = rootElement.querySelector('[data-role="focus-detail"]');
  const focusExampleElement = rootElement.querySelector('[data-role="focus-example"]');
  const promptElement = rootElement.querySelector('[data-role="prompt"]');
  const branchesElement = rootElement.querySelector('[data-role="branches"]');
  const connectorsElement = rootElement.querySelector('[data-role="connectors"]');
  const terminalElement = rootElement.querySelector('[data-role="terminal"]');

  const path = [data.root];

  const countNodes = (node) => 1 + (node.children || []).reduce(
    (total, child) => total + countNodes(child),
    0
  );

  const totalNodes = countNodes(data.root);

  const activeMode = () => {
    for (let index = path.length - 1; index >= 0; index -= 1) {
      if (path[index].mode) return path[index].mode;
    }
    return data.mode;
  };

  const shortLabel = (label) => {
    const clean = label.replace(/^[\d.]+[｜|]\s*/, "").replace(/：.*/, "");
    return clean.length > 12 ? clean.slice(0, 12) + "…" : clean;
  };

  const renderPath = () => {
    pathElement.replaceChildren();
    path.forEach((item, index) => {
      if (index > 0) {
        const separator = document.createElement("span");
        separator.className = "flt-separator";
        separator.textContent = "›";
        separator.setAttribute("aria-hidden", "true");
        pathElement.appendChild(separator);
      }

      const pathButton = document.createElement("button");
      pathButton.type = "button";
      pathButton.className = "btn btn-ghost";
      pathButton.textContent = index === 0
        ? "节点 0 · 根问题"
        : "节点 " + item.id + " · " + shortLabel(item.label);
      pathButton.setAttribute("data-tooltip", item.label);
      pathButton.setAttribute("aria-label", "返回第 " + index + " 层：" + item.label);
      pathButton.addEventListener("click", () => {
        path.splice(index + 1);
        render();
      });
      pathElement.appendChild(pathButton);
    });
  };

  const renderBranches = (current, depth) => {
    branchesElement.replaceChildren();
    current.children.forEach((child) => {
      const choice = document.createElement("button");
      choice.type = "button";
      choice.className = "btn btn-block";
      const branchId = document.createElement("span");
      branchId.className = "flt-branch-id";
      branchId.textContent = "节点 " + child.id;
      const branchLabel = document.createElement("span");
      branchLabel.className = "flt-branch-label";
      branchLabel.textContent = child.label;
      choice.append(branchId, branchLabel);
      choice.setAttribute(
        "aria-label",
        "节点 " + child.id + "，第 " + (depth + 1) + " 层：" + child.label
      );
      choice.addEventListener("click", () => {
        path.push(child);
        render();
      });
      branchesElement.appendChild(choice);
    });
  };

  const render = () => {
    const current = path[path.length - 1];
    const depth = path.length - 1;
    const atLeaf = depth === 5;
    const mode = activeMode();

    depthElement.textContent = "第 " + depth + " / 5 层";
    modeElement.textContent = modeLabels[mode] || "五层三叉";
    countElement.textContent = "完整结构：" + totalNodes + " 个节点 · 每个问题 3 个回答";
    focusLabelElement.textContent = depth === 0
      ? "节点 0 · 根问题"
      : "节点 " + current.id + " · 第 " + depth + " 层 · " + (modeLabels[mode] || "思考");
    focusIdElement.textContent = current.id;
    focusTextElement.textContent = current.label;
    focusDetailElement.textContent = current.detail;
    focusExampleElement.textContent = current.example;
    backButton.disabled = depth === 0;
    homeButton.disabled = depth === 0;
    connectorsElement.hidden = atLeaf;
    branchesElement.hidden = atLeaf;
    terminalElement.hidden = !atLeaf;

    if (atLeaf) {
      promptElement.textContent = "第五层：当前路径递归结束";
    } else if (depth === 0 && data.mode === "mixed") {
      promptElement.textContent = "第一层：是什么、为什么、怎么办";
    } else if (depth === 0) {
      promptElement.textContent = "第一层：三个直接回答";
    } else {
      promptElement.textContent = prompts[mode] || prompts.mixed;
    }

    renderPath();
    if (!atLeaf) renderBranches(current, depth);
  };

  backButton.addEventListener("click", () => {
    if (path.length > 1) {
      path.pop();
      render();
    }
  });

  homeButton.addEventListener("click", () => {
    path.splice(1);
    render();
  });

  copyButton.addEventListener("click", async () => {
    const current = path[path.length - 1];
    const reference = "节点 " + current.id + "：" + current.label;
    let copied = false;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(reference);
        copied = true;
      } catch (_error) {
        copied = false;
      }
    }
    if (!copied) {
      const textArea = document.createElement("textarea");
      textArea.value = reference;
      textArea.setAttribute("readonly", "");
      textArea.style.position = "fixed";
      textArea.style.opacity = "0";
      rootElement.appendChild(textArea);
      textArea.select();
      copied = document.execCommand("copy");
      textArea.remove();
    }
    const originalText = copyButton.textContent;
    copyButton.textContent = copied ? "已复制节点引用" : "请手动复制节点编号";
    setTimeout(() => {
      copyButton.textContent = originalText;
    }, 1600);
  });

  render();
})();
</script>
'''

    return (
        template.replace("__WIDGET_ID__", widget_id)
        .replace("__ARIA_LABEL__", html.escape(f"{title}：五层三叉思考模型", quote=True))
        .replace("__DATA_JSON__", data_json)
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a validated five-level ternary tree as an HTML fragment."
    )
    parser.add_argument("--input", required=True, type=Path, help="Input JSON path")
    parser.add_argument("--output", required=True, type=Path, help="Output HTML path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = load_and_validate(args.input)
        fragment = render_fragment(data)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(fragment, encoding="utf-8")
    except (OSError, TreeValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "nodes": EXPECTED_NODE_COUNT,
                "depth": MAX_DEPTH,
                "mode": data["mode"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
