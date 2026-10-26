# 一份稿件，生成两个发布页

新任务只维护项目 `task-plan.json`、每篇 `canonical/article.md` 和图片。G 保存并绑定用户原确认，W 只读要求、写本篇；不要求新任务初始化机架、填写审稿索引或维护多层哈希链。旧 campaign.json 项目继续原接口，见文末。

## 一次确认，集中生成与检查

G 在项目根保存一份已向用户展示的方案。共享要求只写一次，逐篇写平台、语言、读者任务和差异；可用模板 `templates/task-plan.json`。它是要求来源，不是文章质量证明。用户明确确认完整方案后，G 保存原回复为 `owner-confirmation.txt`，用同一轻量工具绑定：

```sh
python skills/blog-writer/scripts/build_release.py --plan /项目/task-plan.json --freeze --receipt-file /项目/owner-confirmation.txt --source 用户原消息定位
```

绑定文件由程序维护。程序只能检测方案/回复是否改变，不能鉴别消息是否来自用户；G 必须核对真实原回复，不把自己写的文本或状态当授权。方案修改涉及已确认要求时先取得新确认，不能先重绑再声称已授权。W 不运行确认命令。

作者只需：

```sh
python skills/blog-writer/scripts/build_release.py --plan /项目/task-plan.json --article-id A01 --brief
python skills/blog-writer/scripts/build_release.py --plan /项目/task-plan.json --article-id A01 --verify-images
```

第一条可选：G 已给完整本篇任务时不用运行。第二条在图片已上传并填写真实 `public_url` 后核验图片、生成完整 HTML/Markdown 全文，并报告链接次数、正文图与封面。随后用不带 `--verify-images` 的命令加 `--check` 核对当前成品。图片未备齐时只用 `--local-preview` 在 `preview/` 看草稿。

## 作者的一份 Markdown

位于 `articles/A01/canonical/article.md`。顶部 `---json` / `---` 信息块只保存 SEO title、tags、description、excerpt（文章摘要）、图片文件/Alt/图注、封面及真实来源说明；之后一个 `# 标题` 和普通 Markdown 正文。格式见 `templates/author-draft.md`，不自行开发 HTML 壳、CSS、按钮。

`# 标题`是文章可见主标题/预期 H1，信息块的 `seo_title`是独立页面标题。编译器将前者放在可复制标题区，后者放在页面 `<title>` 和 SEO 信息区。精简方法及平台只有一个标题栏时的处理见[标题标准](editorial-standard.md#分开写页面-seo-title-与文章-h1)。

正文准确位置用单独的 `<!-- BLOG_3P_IMAGE:01 -->` 等编号标记，生成时替换为真实图片。图片放本篇目录，命名如 `images/01-lead-topic.png`、`02-middle-topic.jpg`、`03-closing-topic.png`；额外封面为 `00-cover-topic.png`，不能顶替正文首图。素材真实 PNG/JPG/JPEG，Alt/图注按文章语言写，文件和操作资料仅在正文外展示。数量和覆盖按确认方案执行。

新稿必填 `excerpt`：用文章语言写一段简短摘要，供平台摘要栏或文章卡片使用，准确概括正文的读者问题和帮助，不新增未经支持的承诺。它与搜索结果用的 SEO description 分开保存，不机械照抄，也不强求完全不同；不新增字数/字符门槛。摘要位于页面底部，不混入正文。旧稿无此字段时保持兼容，不自动补写或重编译历史交付。

来源信息块的 URL 不自动变成正文超链接。每条重要主张须有适用来源；品牌用语不证明当地需求、热度或实测效果。记录必要引用，不拆成逐句台账。示例性质集中说明，限制只保留影响读者操作的内容。

## 公开图片与完整图文页

新任务方案设置 `delivery_requirements.public_image_urls_required: true`。W 按[图片托管](image-hosting.md)自行选择可用图床，上传可公开的最终正文图和封面，在每张图片记录中填真实 `public_url`。使用生成命令加 `--verify-images` 匿名核验并生成完整图文页；后续 `--check` 复用检查记录，地址或素材有变时重新核验。

HTML 在文内原位显示图片；Markdown 在同一位置写对应公开图片引用。两份包含完整全文与读者图注，正文内没有操作卡、文件名或上传说明。可见 Alt、URL 等图片资料在正文外单列，封面单独展示。正式交付默认要求公开 URL；草稿用 `--local-preview`，旧文件保持原样。

## 保真与一次质量核验

CTA/披露、语言、平台、关键词要求和链接数量只来自 G 维护的确认方案，不能在稿件信息块另行定义。正文须实际保留必需 CTA 和披露。目标站介绍、推荐、来源链接全部按出现次数合并，同一 URL 重复三次就是三处。只有用户明确约定才设准确数量或上限；无约定不猜“一条”。裸目标 URL 可能被平台自动链接，有数量约定时先消除歧义。

新任务的目标产品文字外链须在可点击文字内含已确认品牌名。轻量工具默认用 `cta.product_name` 检查目标域名；若产品名称与品牌不同、有已确认的品牌别名或多个目标品牌，在原 `link_policy.target_brand_names` 按域名填写名称列表，例如 `{"flyne.ai": ["Flyne", "Flyne AI"]}`。只填已确认写法，不从域名猜简称；更具体的子域名配置优先。其他声明为目标的域名也需对应名称。程序默认检查该规则，漏填映射不会关闭；没有品牌的锁定锚文本报冲突，不自动修改。旧索引项目只在明确更新原链接约定后启用映射，不静默改动历史要求。

交付页固定从上到下：博客标题、含真实图片与读者图注的完整正文、SEO title/tags/description、独立 Excerpt（文章摘要），之后单列封面和图片资料。无复制按钮，标题和正文分开复制，正文不重复 H1；无独立标题字段的平台按说明连同标题一起复制。公开页层级看实际渲染。

生成成功不代表质量合格。先生成并检查两份最终载荷、备齐最终图片/封面，随后必须交独立 R；R 不在载荷未完成时先批准源稿。R 以最终可视化 HTML 为主，Markdown 仅作同源备用，不另完整审一遍。通过留短结论和所审生成版本；有问题才记录位置、依据和修复结果。修改后重生成，由原 R 只确认变更和直接依赖，旧结论不自动延伸到新版本；不常规全文复审。当前版本获独立 R 通过后 G 对照原要求验收，才正式交用户发布。隐藏的 `handoff/.build.json` 可引用当前输出指纹，但不是审稿或发布证明，不为这条顺序新增报告或工具。

## 运行与旧项目

Python 3.9+；新 Markdown 路线需要 `markdown-it-py==3.0.0`，依赖文件仍在内部目录 `skills/blog-human-handoff/scripts/requirements.txt`。可用隔离环境安装，不改变模型配置。

已有 `campaign.json`、`article-package.json` 或文章契约的项目不静默迁移。它们才使用内部 `prepare_article.py`、旧编译/校验及原质量绑定，见[旧交付接口](../../blog-human-handoff/REFERENCE.md)和[作者旧接口](execution-details.md)。旧程序路径保留，内部目录不是需要额外加载的技能。
