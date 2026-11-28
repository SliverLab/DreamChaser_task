/*
 * 文章数据:列表页用它做搜索与标签筛选。
 * 每篇文章都有独立详情页,url 可直接打开(需已登录)。
 * body 字段只用于检索:把正文里的关键词收进来,避免导师搜正文词时得到 0 结果。
 */
window.ARTICLES = [
  {
    title: 'MCP 是怎么把模型和工具接起来的',
    url: 'articles/mcp-basics.html',
    tags: ['MCP', '基础'],
    excerpt: 'MCP 用 JSON-RPC 2.0 通信,服务端提供三类能力:工具、资源、提示词。传输方式有 stdio、SSE 和 streamable HTTP 三种。',
    body: 'JSON-RPC 2.0 tools resources prompts stdio SSE streamable HTTP 子进程 标准输入输出 上下文'
  },
  {
    title: 'Playwright MCP 的默认超时:动作 5 秒,导航 60 秒',
    url: 'articles/playwright-mcp.html',
    tags: ['MCP', '超时'],
    excerpt: 'Playwright MCP 默认以有界面模式启动,动作超时 5000 毫秒、导航超时 60000 毫秒,可用 --timeout-action 与 --timeout-navigation 调整。',
    body: '5000 60000 毫秒 timeout-action timeout-navigation headed 有界面 超时后报错 Timeout exceeded'
  },
  {
    title: '为什么按快照里的 ref 点击,而不是按屏幕坐标',
    url: 'articles/snapshot-ref.html',
    tags: ['定位', '快照'],
    excerpt: '快照来自浏览器无障碍树,元素带 ref 编号。坐标会随窗口大小和布局变化而失效,ref 在页面变化后也需要重新快照。',
    body: '无障碍树 ref e12 坐标 resolution 滚动 重新快照 role 可访问名称 视口'
  },
  {
    title: '源名单不是沙盒:allowed-origins 到底拦住了什么',
    url: 'articles/permission-sandbox.html',
    tags: ['权限', '安全'],
    excerpt: 'allowed-origins 只过滤浏览器准备请求的源,官方明确说明它不构成安全边界,也不影响重定向,不能替代产品层审批。',
    body: 'allowed-origins 分号 安全边界 重定向 隔离 审批 工作目录 用户数据目录'
  },
  {
    title: '登录态复用的两条路:user-data-dir 与 storage state',
    url: 'articles/storage-state.html',
    tags: ['会话', '登录'],
    excerpt: '不指定 user-data-dir 时 Playwright 会建一个临时配置目录,关掉即失;要复用登录态,需要固定目录或显式保存 storage state。',
    body: 'user-data-dir storage state Cookie localStorage 临时目录 gitignore 会话 凭据'
  },
  {
    title: '提示词注入:页面上的文字是资料,不是指令',
    url: 'articles/prompt-injection.html',
    tags: ['安全', '注入'],
    excerpt: '网页里出现"忽略之前的指令"这类文字时,Agent 应当把它当数据而不是命令。防护要在工具层和审批层做,不能只靠提示词。',
    body: '忽略之前的指令 example.com 注入 不可信输入 审批 权限 执行 快照 低对比度'
  },
  {
    title: '无头模式还是有界面:人工登录时该选哪个',
    url: 'articles/headless-vs-headed.html',
    tags: ['基础', '浏览器自动化'],
    excerpt: 'Playwright MCP 默认是有界面模式,窗口真的会弹出来。无头省的是绘制开销,不是登录时间;任务里只要含人工输入凭据或验证码,就必须有界面。',
    body: '无头 headless headed 有界面 窗口 人工登录 验证码 CI isolated storage state 提速 绘制 默认模式'
  },
  {
    title: '工具审批:让危险动作真的停下来',
    url: 'articles/tool-approval.html',
    tags: ['安全', '浏览器自动化'],
    excerpt: '提示词里写「不许删文件」不算数,它只降低概率、不提供保证。真正拦得住的是三层边界:访问过滤、最小权限工作目录、以及工具层或产品层的审批。',
    body: '审批 approve 确认 自动批准 提示词不算 allowed-origins output-dir 工作目录 三层 危险动作 发消息 删除 提交 MCP 工具 读写'
  },
  {
    title: '等待与重试:为什么不能写死 sleep(5)',
    url: 'articles/wait-and-retry.html',
    tags: ['等待', '浏览器自动化'],
    excerpt: 'sleep 的问题不是慢,而是什么都不保证。要等的是可观察的状态,比如某段文字出现或用 browser_wait_for 的 textGone 等加载提示消失;超时后重取快照再试,且有上限。',
    body: 'sleep 等待 textGone browser_wait_for 状态 超时 重试 上限 快照 ref 坐标 可访问名称 墙上的时钟'
  },
  {
    title: '步数上限:25 次工具调用怎么分配',
    url: 'articles/step-budget.html',
    tags: ['额度', '浏览器自动化'],
    excerpt: '浏览器任务很容易越跑越贵:每开一页取一次快照、每改一次条件再取一次。写明步数上限逼 Agent 在预算里取舍,到顶必须停并交出已拿到的结果。',
    body: '步数 工具调用 预算 25 超限 停止 失败 记录 超时 重试 取舍 刷屏 MCP 工具调用次数'
  },
  {
    title: 'output-dir:把 Agent 的写入关进一个抽屉',
    url: 'articles/output-dir-safety.html',
    tags: ['权限', '浏览器自动化'],
    excerpt: 'output-dir 把自动命名的截图和快照收进一个目录,提交时只看这一处。注意它只管自动命名,显式文件名按工作区根解析;越界写必须单独确认。',
    body: 'output-dir 工作目录 写入 越界 最小权限 显式文件名 workspace root 自动命名 gitignore storage state 不受限文件访问'
  },
  {
    title: 'MCP 工具分读和写:审批该拦哪一类',
    url: 'articles/read-vs-write-tools.html',
    tags: ['MCP', '浏览器自动化'],
    excerpt: '按「改不改变外部状态」划线:导航、快照、读文本、等状态都只读,可以一次放行;提交表单、写文件、保存会话会改状态,必须每次确认。',
    body: '读 写 审批 只读 storage 凭据 gitignore opt-in 提交 表单 快照 会话状态 外部状态'
  }
];
