#!/bin/bash
# 双击本文件即可在浏览器里打开 wiki。
#
# 为什么必须走本地服务器而不是直接双击 HTML：
# VitePress 产物的资源和站内链接都是绝对路径（/assets/...、/units/x.html），
# 用 file:// 打开时它们会指向文件系统根目录，导致 CSS 加载不到、链接全部 404
# —— 页面会变成没有样式的裸 HTML 且点不动。这里起一个本地服务器就没这问题。
#
# GitHub Pages 上同理：站点在 /<仓库名>/ 子路径下，构建时 base 必须匹配。

cd "$(dirname "$0")" || exit 1

DIST="docs/.vitepress/dist"

if [ ! -d "$DIST" ]; then
  echo "还没有构建产物，先执行 npm run build ..."
  export PATH=/usr/local/node22/bin:$PATH
  npm run build || { echo "构建失败"; read -n1 -s; exit 1; }
fi

# 找一个空闲端口（4180 起）
PORT=4180
while lsof -i ":$PORT" >/dev/null 2>&1; do
  PORT=$((PORT + 1))
done

URL="http://127.0.0.1:$PORT/"

echo "================================================"
echo "  Mindustry 数据包 Wiki 本地预览"
echo "  地址: $URL"
echo "  关闭本终端窗口即停止服务"
echo "================================================"

cd "$DIST" || exit 1
( sleep 1; open "$URL" ) &
exec python3 -m http.server "$PORT" --bind 127.0.0.1
