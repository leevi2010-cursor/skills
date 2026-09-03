# 输入处理

## 共同记录

三种输入都要记录：来源类型、来源标识、录音日期、时长、转写方式、说话人标识和处理时间。逐字稿缺少时间点或说话人时，明确写出限制。

原音频、完整逐字稿和客户联系方式只保存在私密工作目录。不要打印到普通终端日志，不要放入项目 Git 仓库。

## 逐字稿

1. 保留原有时间点和说话人名称。
2. 没有时间点时，用段落编号引用，不伪造时间。
3. 先识别是否为销售接待，再做身份检查。
4. 同一份文本包含多个客户或多个独立场景时，先询问怎样拆分。

## 本地录音

1. 计算 SHA-256，并读取时长、声道和格式。
2. 运行 `scripts/ensure_local_transcription.sh`。脚本只在缺失时安装当前 Apple Silicon 环境需要的 `ffmpeg` 和 `mlx-whisper`，不使用 `sudo`。
3. 用 `ffmpeg -i` 检查文件能否读取。
4. 在私密工作目录执行：

```bash
mlx_whisper <relative-audio-path> \
  --model mlx-community/whisper-large-v3-turbo \
  --language zh \
  --word-timestamps True \
  --output-format json \
  --output-dir <relative-private-output-dir>
```

5. 本机当前没有可靠的说话人分离工具。转写结果不能自动证明谁是客户、谁是销售；必须经过身份门槛。
6. 抽听涉及金额、日期、产品名、地址、承诺和下一步的区段。

## 飞书妙记

1. 从 URL 提取 `minute_token`。
2. 读取 `lark-minutes` Skill 及 `+detail`、`+download` 对应 reference。
3. 先下载逐字稿：

```bash
env -u HERMES_HOME lark-cli minutes +detail \
  --minute-tokens <token> --transcript --output-dir <relative-private-dir> \
  --profile "$SHOWROOM_LARK_PROFILE" --as "$SHOWROOM_LARK_ACTOR"
```

4. 再下载原录音：

```bash
env -u HERMES_HOME lark-cli minutes +download \
  --minute-tokens <token> --output-dir <relative-private-dir> \
  --profile "$SHOWROOM_LARK_PROFILE" --as "$SHOWROOM_LARK_ACTOR"
```

5. 分析必须基于逐字稿，不照搬飞书 AI 总结。
6. 原录音用于核对关键区段，不因下载成功就推定说话人身份正确。
