<div align="center">
  <h1>DigitalPlat 免费域名自动续期</h1>
  <p>每周自动检查 DigitalPlat 域名，到期前自动免费续期</p>
  <p>简体中文 | <a href="README.en.md">English</a></p>
  <p>
    <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-3776AB">
    <img alt="Platform" src="https://img.shields.io/badge/platform-GitHub%20Actions-2088FF">
    <img alt="License" src="https://img.shields.io/badge/license-MIT-111827">
    <img alt="Schedule" src="https://img.shields.io/badge/schedule-Weekly-22c55e">
  </p>
</div>

> 只需 3 分钟部署，之后每周自动检查并续期你的 DigitalPlat 免费域名。

## 3 分钟部署

### 第 0 步：创建 DigitalPlat API Token

打开：

* <https://dash.domain.digitalplat.org/dashboard/api/keys>

创建一个 API Key，通常是 `dp_live_...` 开头。文档页位于：

* <https://dash.domain.digitalplat.org/dashboard/api/docs>

本项目使用 Bearer Token 调用 DigitalPlat API。

### 第 1 步：把仓库设为私有仓库

**1-1. 打开 GitHub Importer**

1. 登录 GitHub。
2. 打开：<https://github.com/new/import>

**1-2. 填写导入信息**

| 字段                                | 填什么                                                         |
| --------------------------------- | ----------------------------------------------------------- |
| `Your old repository's clone URL` | `https://github.com/OUBIGFA/DigitalPlat-Domains-auto-renew` |
| `Owner`                           | 你的 GitHub 账号                                                |
| `Repository name`                 | 你的仓库名，例如 `my-digitalplat-auto-renew`                        |
| `Privacy`                         | 选 `Private`                                                 |

然后点击 `Begin import`，通常几十秒到几分钟会完成。

### 第 2 步：配置 GitHub Secret 和 Variable

进入：

* `Settings -> Secrets and variables -> Actions`

添加 Secret：

* `DIGITALPLAT_API_TOKEN`

添加 Variable：

* `DIGITALPLAT_DOMAINS`

`DIGITALPLAT_DOMAINS` 一行一个域名：

```text
example.dpdns.org
example.qzz.io
```

可选 Variable：

* `DIGITALPLAT_RENEW_BEFORE_DAYS`：默认 `120`

### 第 3 步：手动运行一次

打开 GitHub 的 `Actions`，手动运行 `DigitalPlat Auto Renew`。

第一次运行会检查域名并生成 `state/domains-state.json`。之后工作流每周一 UTC 04:17 自动运行一次。

## 续期规则

默认规则：

* 免费续期窗口：到期前 `120` 天

* 每周检查一次

* 只有进入窗口后才会请求续期

* 默认调用 `renewal_type=free`、`years=1`

如果域名还没进入窗口，脚本只记录检查状态，不会调用续期接口。

## 文件说明

* `scripts/digitalplat_auto_renew.py`：续期脚本

* `.github/workflows/digitalplat-auto-renew.yml`：每周 GitHub Actions 工作流

* `state/domains-state.json`：运行后自动生成的状态文件

## API 说明

当前实现使用 DigitalPlat Domain API：

* `GET /domains`

* `GET /domains/{domain}`

* `POST /domains/{domain}/renew`

默认 API Base：

* `https://domain-api.digitalplat.org/api/v1`

如果官方文档后续调整 API Base，可在 GitHub Variables 里添加 `DIGITALPLAT_API_BASE` 并同步修改 workflow 环境变量。

## 许可证

本项目使用 MIT License。

***

[linux.do](https://linux.do)
