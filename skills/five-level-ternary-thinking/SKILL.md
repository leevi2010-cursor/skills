---
name: five-level-ternary-thinking
description: Apply the 五层三叉思考模型 to substantive open-ended questions framed as “是什么”, “为什么”, or “怎么办”, including equivalent requests to define something, explain causes, or develop solutions. Build an exact five-level ternary tree in plain language a high-school graduate can understand, give every focused node a detailed explanation, a relatable example, and a stable path number, render it as interactive HTML, and always deliver both an inline visualization and a clickable standalone HTML file. Do not use for simple factual lookups, one-step calculations, or when the user explicitly requests plain text only.
---

# 五层三叉思考模型

Turn one substantive question into an exact five-level ternary reasoning tree and an interactive HTML view. Treat the model as an exploration and decision aid, not as proof that every generated branch is true.

## Workflow

1. Identify the focal question and the dominant mode:
   - `what`: asks what something is, contains, means, includes, or looks like.
   - `why`: asks for causes, mechanisms, conditions, or persistence.
   - `how`: asks what to do, how to act, improve, prevent, detect, or correct.
   - `mixed`: explicitly requests two or all three modes. Use three level-one branches labeled 是什么, 为什么, and 怎么办 when all three are requested; otherwise choose the user's final or dominant intent.
2. Resolve only ambiguity that would materially change the tree. Prefer a reasonable interpretation over a blocking question.
3. Gather current or high-stakes evidence before drafting when the subject requires it. Distinguish sourced facts, inferences, hypotheses, and value choices. Never fabricate specificity merely to fill the tree.
4. Read [references/model-rules.md](references/model-rules.md) completely.
5. Draft one data object with this shape:

```json
{
  "title": "Concise title",
  "mode": "what",
  "root": {
    "label": "The focal question",
    "detail": "A plain-language explanation in 1–3 short sentences",
    "example": "A concrete, widely relatable example",
    "children": [
      {
        "label": "First answer",
        "detail": "Why or how this directly answers the parent",
        "example": "An everyday example",
        "children": []
      },
      {
        "label": "Second answer",
        "detail": "A distinct second answer explained plainly",
        "example": "A different everyday example",
        "children": []
      },
      {
        "label": "Third answer",
        "detail": "A distinct third answer explained plainly",
        "example": "A third everyday example",
        "children": []
      }
    ]
  }
}
```

6. Expand the root through level 5. Give every node at levels 0–4 exactly three children and every node at level 5 no children. The complete tree must contain 364 nodes. Give every node non-empty `label`, `detail`, and `example` fields.
   - For `mixed`, add `"mode": "what"`, `"mode": "why"`, and `"mode": "how"` to the corresponding level-one nodes. A node-level mode overrides the top-level mode for that branch.
   - Do not write node IDs manually. The renderer assigns stable path numbers: root `0`, then `1`, `1.1`, `1.1.1`, and so on.
7. Write for a high-school graduate. Prefer familiar words and short sentences. Define an unavoidable technical term in the same sentence. Make siblings distinct, complementary, and at the same abstraction level. Do not disguise synonyms as three answers. Ensure each child directly answers its parent in the active mode.
8. Write the data object to a temporary JSON file using the host's approved file-editing mechanism.
9. Resolve `scripts/render_tree.py` relative to this `SKILL.md`, then render and validate with its absolute path:

```bash
python3 <this-skill-directory>/scripts/render_tree.py \
  --input <absolute-input.json> \
  --output /workspace/five-level-ternary-<short-slug>.html
```

10. Re-read the generated script block and run a JavaScript syntax check. Do not present an invalid visualization.
11. Expose the validated HTML as a user-accessible standalone file. Use the active product's supported file-link or attachment mechanism; never give only a plain filesystem path. In ChatGPT Work mode, link the absolute rendered path with a `sandbox:` Markdown target. Keep the standalone file and inline visualization based on the same validated HTML output.
12. Lead the final response with one concise conclusion or framing sentence. Then always attempt the inline visualization and always provide the standalone HTML link immediately below it:

```text
<concise conclusion>

visualize{"path":"/workspace/five-level-ternary-<short-slug>.html"}

[打开独立 HTML 交互图](sandbox:/workspace/five-level-ternary-<short-slug>.html)

如果上方交互图未显示，请使用独立 HTML 链接。
```

13. Never make the standalone link conditional on the user asking for a link or download. Never substitute the inline visualization for the file link, or the file link for the inline visualization. If inline rendering is unavailable, still deliver the standalone HTML and state that it is the fallback.

## Content Rules

- Preserve the user's wording at the root while clarifying grammar silently.
- Use short node labels that still carry a complete idea. Prefer 8–24 Chinese characters when practical.
- Use ordinary language that a high-school graduate can understand on first reading. Replace or immediately explain abstract terms such as “元认知”, “路径依赖”, “目标函数”, or “系统性风险”.
- Write `detail` as 1–3 short sentences that explain what the label means, how it connects to its parent, and what observable sign would support it. Do not merely repeat the label.
- Write `example` as one concrete situation common to study, work, family, consumption, relationships, or everyday decisions. Make the person, action, and result visible. Do not use another abstract statement as the example.
- Vary examples across sibling groups. Prefer situations many people have experienced over niche professional examples.
- Let depth add information:
  - Level 1: three direct answers.
  - Level 2: three major subanswers under each direct answer.
  - Level 3: mechanisms, tactics, components, or conditions.
  - Level 4: implementation details, evidence channels, safeguards, or observable dimensions.
  - Level 5: atomic explanations, actions, indicators, examples, or verification steps.
- Use uncertainty language such as “可能”, “假设”, or “需验证” when evidence is incomplete.
- Allow different branches to converge on the same deep mechanism, but avoid copy-pasted labels and generic filler.
- For `how`, make actions feasible and specify a decision signal, safeguard, or next step by the lower levels.
- For `why`, keep causal direction correct. Do not replace a cause with a symptom or restatement.
- For `what`, explain identity, composition, boundary, process, variation, or observable form. Do not drift into causes unless the user's concept requires them.
- Do not claim the three branches are exhaustive. They are the three highest-value lenses chosen for the current question.

## Quality Gate

Before rendering, verify all of the following:

- The root matches the user's real question.
- The chosen mode is correct.
- Every non-leaf has exactly three children.
- The deepest leaves are at level 5 and the total is 364 nodes.
- No sibling group contains duplicates or near-synonyms.
- Each level is more concrete or more explanatory than its parent.
- Every node contains a plain-language `detail` and a relatable `example`, neither identical to its label.
- The renderer assigns one unique path number to all 364 nodes and shows it in the focused node, branch buttons, and breadcrumbs.
- A reader can cite a node unambiguously with a phrase such as “节点 2.1.3”.
- Factual, causal, and action claims are not presented with more certainty than the evidence supports.
- The HTML is responsive, keyboard-accessible, theme-aware, and focused on the tree.
- The final response contains both the inline visualization reference and a clickable standalone `.html` link.
- The standalone link resolves to the same validated HTML file, not a plain path, placeholder, or different export.
- The fallback sentence tells the user to use the standalone link if the inline view does not display.

If the model cannot produce a meaningful five-level tree without inventing facts, explain the limitation and ask whether the user wants a shallower version. Do not pad the tree.
