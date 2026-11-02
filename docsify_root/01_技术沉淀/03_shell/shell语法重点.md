# Shell 语法重点

## 1. Shebang 与脚本入口

```bash
#!/bin/bash
```
- 写在文件第一行，告诉系统“用 `/bin/bash` 来解释执行我”。
- 三种脚本都用 `#!/bin/bash`（bash，功能比 `sh` 多，支持 `[[ ]]`、数组等）。

---

## 2. 变量与命令替换

### 2.1 `$(...)` 命令替换
```bash
APP_HOME=$(cd "$(dirname "$0")" && pwd)
```
- `$(命令)` 会先执行里面的命令，把**输出结果**替换到当前位置。
- 嵌套示例：`$(dirname "$0")` 先拿到“脚本所在目录名”，外面再 `cd` 进去并 `pwd` 得到绝对路径。
- **为什么不用 `$PWD`？** `$PWD` 是当前 shell 的工作目录，如果用户在其他目录调用 `./xxx/start_app.sh`，`$PWD` 就不对了；用 `$(dirname "$0")` 才能稳定拿到脚本自己的位置。

### 2.2 特殊位置参数
| 符号 | 含义 | 脚本里的用途 |
|------|------|--------------|
| `$0` | 脚本自身路径 | `readlink -f "$0"` 拿绝对路径，用于 monitor 里回调自己 |
| `$1` | 第 1 个参数 | `start` / `stop` / `restart` |
| `$2` | 第 2 个参数 | `monitor` 标志 |
| `$?` | 上一条命令的返回值 | `local result=$?` 捕获函数/命令成功与否（0=成功） |
| `$!` | 上一个后台进程的 PID | `echo $! > "$PID_FILE"` 记录刚启动的进程 |
| `$$` | 当前脚本自身的 PID | 写进锁文件 `echo "$$" > "$LOCK_DIR/pid"` |
| `${1:-}` | 若 `$1` 未设置则用空串 | `case "${1:-}"` 避免未传参时报错（配合 `set -u`） |

### 2.3 `local` 局部变量
```bash
start_app() {
    local monitor_flag=$1
    local attempts=0
}
```
- 函数内用 `local` 声明变量，作用域只在该函数内，不会污染全局。
- 三套脚本大量使用，是写好函数的好习惯。

---

## 3. 条件判断 `[[ ... ]]`

Bash 推荐用双中括号 `[[ ]]`（比单中括号 `[ ]` 更智能，不需要对变量加引号也不会词分裂出错）。

### 3.1 常用文件/字符串测试符
| 写法 | 含义 |
|------|------|
| `[[ -f "$FILE" ]]` | 文件存在且是普通文件 |
| `[[ -x "$FILE" ]]` | 文件有可执行权限 |
| `[[ -d "/proc/$pid" ]]` | 目录存在（用 `/proc/$pid` 是否存在来判断进程活着） |
| `[[ -n "$pid" ]]` | 字符串非空 |
| `[[ -z "$PID" ]]` | 字符串为空 |
| `[[ "$a" == "b" ]]` | 字符串相等 |
| `[[ "$a" != "a" && "$a" != "b" ]]` | 逻辑与（同时满足） |

### 3.2 短路写法（非常重要，脚本里到处都是）
```bash
[[ -n "$pid" ]] && ps -p "$pid" > /dev/null 2>&1
```
- `A && B`：A 为真才执行 B（类似“如果 A 就 B”）。
- `A || true`：A 失败也不让脚本因为“命令返回非0”而退出（常用于 `kill ... || true`）。
- `command -v fuser >/dev/null 2>&1`：`command -v 名字` 用来检测“某个命令是否存在”，存在则打印路径并返回0。

---

## 4. 流程控制

### 4.1 `case ... esac`（主入口分发）
```bash
case "${1:-}" in
    start)   start_app "$2" ;;
    stop)    stop_monitor; stop_app ;;
    restart) restart_app "$2" ;;
    *)       echo "Usage: $0 {start|stop|restart} [monitor]"; exit 1 ;;
esac
```
- 根据第一个参数 `$1` 选择执行哪段逻辑，`;;` 相当于其他语言的 `break`。
- `*` 是“兜底/默认”分支，参数不对就打印用法并退出。

### 4.2 `if ... then ... fi`
```bash
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [[ -z "$PID" ]]; then
        rm -f "$PID_FILE"
        return
    fi
fi
```

### 4.3 `while` 循环（重试 / 轮询）
```bash
local attempt=1
while [[ $attempt -le 3 ]]; do
    # 尝试启动...
    ((attempt++))        # 算术自增
done
```
- `((attempt++))` 是算术运算写法，等价于 `attempt=$((attempt+1))`。
- 优化版用整数计数轮询：`while (( loops < STARTUP_MAX_LOOPS )); do ... loops=$((loops+1)); done`。

### 4.4 `for ... in` 循环
```bash
for partition in a b; do
    target=$(partition_app_path "$partition") || continue
    # ...
done
```
- `|| continue`：如果前面命令失败，就跳到下一次循环。

---

## 5. 函数定义与返回值

```bash
is_process_alive() {
    local pid=$1
    if [[ -n "$pid" ]] && ps -p "$pid" > /dev/null 2>&1; then
        return 0   # 0 = 真/存活
    else
        return 1   # 非0 = 假/不在
    fi
}
```
- 函数名后加 `()`，函数体用 `{ }`。
- 用 `return 0/1` 返回“成功/失败”，调用方用 `if 函数名; then ...` 判断。
- 想返回“数据”而不是“状态”，用 `echo` 输出 + 调用方 `var=$(函数名)` 捕获（如 `partition_dir`、`find_app_pids` 返回 PID 列表）。

---

## 6. 后台运行与进程管理

### 6.1 `nohup ... &`（脱离终端的后台进程）
```bash
nohup bash -c "
    while true; do
        # 看门狗死循环...
    done
" > "$APP_HOME/monitor.log" 2>&1 &
echo $! > "$MONITOR_PID_FILE"
```
- `&`：把命令放到后台执行，脚本不等待它，立刻继续往下走。
- `nohup`：忽略 `SIGHUP` 信号，关掉 SSH/串口终端后进程也不会被杀。
- `> file 2>&1`：把标准输出(1)和错误输出(2)都重定向到文件。
- `echo $!`：把刚启动的后台进程 PID 记下来，方便以后停止它。

### 6.2 `setsid`（新建会话，彻底脱离）
```bash
setsid "$start_script" >/dev/null 2>&1 &
local launcher_pid=$!
```
- `setsid` 让子程序拥有**独立会话 ID**，父 shell 退出也不会带走它，是做“守护进程”的常用手段。
- 注意：这里 `$!` 拿到的是 `setsid`/启动脚本的 PID（叫 launcher_pid），**不一定是业务程序本身的 PID**——这正是基础版和优化版最大的区别之一（见优缺点文档）。

### 6.3 信号：优雅停止
```bash
kill "$PID"          # 发 SIGTERM（默认），请进程自己优雅退出
kill -9 "$PID"       # 发 SIGKILL，强制杀死（最后手段）
pkill -TERM -P "$PID"  # 给“父进程是 $PID”的所有子进程发 TERM
```
- 标准做法是先 `SIGTERM` 等一会，不行再 `SIGKILL`，避免数据丢失。

### 6.4 `trap`（信号钩子 / 清理）
```bash
trap 'release_lock' EXIT
trap 'release_lock; exit 130' INT
trap 'release_lock; exit 143' TERM
```
- 注册“当脚本收到某信号 / 正常退出(EXIT) 时，先执行 `release_lock` 释放锁”。
- 保证异常退出也不会留下死锁文件。

---

## 7. 用 `/proc` 文件系统判断进程（Linux 专属，三套脚本核心）

```bash
# 进程是否活着：看 /proc/$pid 目录在不在
[[ -n "$pid" ]] && [[ -d "/proc/$pid" ]]

# 进程是不是我们的 gx_charger：看它的可执行文件路径
link=$(readlink "/proc/$pid/exe" 2>/dev/null || true)
[[ "$link" == "$target" || "$link" == "$target (deleted)" ]]
```
- Linux 每个进程在 `/proc` 下有一个以 PID 命名的目录。
- `/proc/$pid/exe` 是指向该进程可执行文件的软链接；程序文件被替换但进程还在时，链接会带 `(deleted)` 后缀，脚本特意兼容这种情况。
- 优化版还读 `/proc/$pid/comm`（进程名，最多 15 字符）做预过滤，避免对每个进程都 `readlink`。

---

## 8. 文件锁（防并发）：`mkdir` 当锁

```bash
if mkdir "$LOCK_DIR" 2>/dev/null; then
    LOCK_HELD=1
    echo "$$" > "$LOCK_DIR/pid"
    # ...
    return 0
fi
```
- `mkdir` 创建目录在文件系统层面是**原子操作**：两个进程同时 `mkdir` 同一个目录，只有一个会成功，另一个必然失败。
- 因此“能建目录=拿到锁”，删目录=释放锁。比用普通文件标志更可靠。
- 若锁目录已存在但持有者进程已死，则删掉旧锁重试一次（防止死锁）。

---

## 9. 安全与调试开关

```bash
set -u                 # 引用未定义变量直接报错退出（避免把空串当有效值）
export PS4='+ $(date +"%s.%3N") L$LINENO: '
# set -x              # 取消注释可打印每一条执行的命令及行号，调试神器
```
- `set -u`：基础版没开，优化版都开了——这是健壮性的重要提升。
- `set -x`：调试时打开，会逐行打印实际执行的命令，配合 `PS4` 还能带上时间戳和行号。

---

## 10. 其他零散但常用的小语法

| 写法 | 作用 |
|------|------|
| `tr -d '[:space:]' < file` | 删除文件内容里的所有空白字符（读分区标记时防换行/空格） |
| `stat -c%s "$FILE"` | 取文件字节大小（用于 20MB 日志轮转判断） |
| `mv "$LOG" "$LOG.bak"` | 日志轮转：旧日志改名备份 |
| `echo "$msg" \| tee -a "$LOG"` | 同时输出到屏幕和追加写入日志 |
| `${var#/proc/}` | 删掉变量开头 `/proc/` 前缀（从 `/proc/123/exe` 取 PID 用） |
| `< <(命令)` | 进程替换，把命令输出当文件喂给 `while read`（优化版1 `find_app_pids` 用过） |
| `2>/dev/null \|\| true` | 忽略错误、不让脚本因非零返回而退出 |
| `command -v pgrep` | 检测系统有没有 `pgrep` 命令，没有就走兼容分支 |

---

## 11. 小结：新手最该先记住的 5 条

1. `$(...)` 取命令结果；`$0/$1/$?/$!` 是脚本的“传感器”。
2. 判断文件/字符串用 `[[ ... ]]`，用 `&&`/`||` 做短路。
3. 函数用 `local` 防污染；用 `return 0/1` 表状态，`echo`+`$()` 表数据。
4. 后台用 `&`/`nohup`/`setsid`；停进程先 `kill` 再 `kill -9`。
5. 优化版比基础版强在三点：**真实 PID**、**进程名校验防误杀**、**文件锁防并发**。
