#!/usr/bin/env python3
"""
链接完整性检查器：遍历 dist 下所有 HTML，抽出每个 href/src，
逐个发真实 HTTP 请求，报告 404 / 断链。

比截图更硬：截图能看出"长得丑"，但看不出"哪个链接是死的"。
用法：
    python3 tools/check_links.py            # 自动起临时服务器并全量检查
"""
import http.server
import os
import re
import socketserver
import sys
import threading
import urllib.parse
import urllib.request
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.normpath(os.path.join(ROOT, '..', 'docs', '.vitepress', 'dist'))

HREF_RE = re.compile(r'(?:href|src)\s*=\s*"([^"]+)"')

# 这些是外链或不参与本站完整性判断的
SKIP_PREFIX = ('http://', 'https://', '//', 'mailto:', 'data:', 'javascript:', '#')


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(directory):
    handler = lambda *a, **kw: Quiet(*a, directory=directory, **kw)
    httpd = socketserver.TCPServer(('127.0.0.1', 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def collect_pages():
    pages = []
    for dirpath, _, files in os.walk(DIST):
        for f in files:
            if f.endswith('.html'):
                pages.append(os.path.relpath(os.path.join(dirpath, f), DIST))
    return sorted(pages)


def main():
    if not os.path.isdir(DIST):
        print('!! dist 不存在，先 npm run build')
        return 1

    httpd, port = serve(DIST)
    base = f'http://127.0.0.1:{port}'

    pages = collect_pages()
    print(f'站点根: {DIST}')
    print(f'HTML 页数: {len(pages)}   临时服务器: {base}')
    print()

    status_cache = {}

    def check(url):
        if url in status_cache:
            return status_cache[url]
        try:
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=10) as r:
                code = r.status
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception as e:
            code = f'ERR:{type(e).__name__}'
        status_cache[url] = code
        return code

    broken = defaultdict(list)
    ext_links = set()
    total_links = 0

    def to_url(page, link):
        """把页面里的链接解析成站点内的绝对 URL；外链返回 None。"""
        if link.startswith(SKIP_PREFIX):
            if link.startswith(('http://', 'https://')):
                ext_links.add(link)
            return None
        # 链接是站点绝对路径（/units/x.html）或相对路径
        if link.startswith('/'):
            path = link
        else:
            path = '/' + os.path.normpath(os.path.join(os.path.dirname(page), link))
        path = path.split('#')[0].split('?')[0]
        if not path:
            path = '/'
        return path

    for page in pages:
        html = open(os.path.join(DIST, page), encoding='utf-8', errors='replace').read()
        links = set(HREF_RE.findall(html))
        page_url = '/' + page.replace(os.sep, '/')

        for link in links:
            path = to_url(page, link)
            if path is None:
                continue
            total_links += 1
            code = check(base + path)
            if code != 200:
                broken[page_url].append((link, path, code))

    print(f'内部链接检查 {total_links} 次（去重后 URL {len(status_cache)} 个）')
    print()
    if broken:
        print(f'!! 有 {len(broken)} 个页面存在断链：')
        for page in sorted(broken):
            print(f'  {page}')
            for link, path, code in broken[page][:8]:
                print(f'      {code}  {link}  ->  {path}')
            if len(broken[page]) > 8:
                print(f'      ... 还有 {len(broken[page]) - 8} 条')
    else:
        print('OK 所有内部链接都返回 200')

    print()
    print(f'外链 {len(ext_links)} 个（不检查）：{sorted(ext_links)[:5]}')

    httpd.shutdown()
    return 1 if broken else 0


if __name__ == '__main__':
    sys.exit(main())
