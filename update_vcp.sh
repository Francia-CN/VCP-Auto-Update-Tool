#!/usr/bin/env bash
# VCP 自动更新工具 v1.0 (Linux/macOS)
# 许可: MIT
# 描述: 用于自动更新 VCPChat 和 VCPToolBox 项目的交互式脚本

# 严格模式 - 但允许更细粒度的错误处理
set -euo pipefail
IFS=$'\n\t'

# ============================================================================
# 全局配置和常量
# ============================================================================

readonly SCRIPT_VERSION="v1.0"
readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly VCP_ROOT="$(dirname "$SCRIPT_DIR")"
readonly LOCK_FILE="$SCRIPT_DIR/.update_vcp.lock"
readonly PID_FILE="$SCRIPT_DIR/.update_vcp.pid"

# 系统信息
readonly OS_TYPE="$(uname -s)"
readonly OS_VERSION="$(uname -r)"
readonly ARCH="$(uname -m)"

# 默认值
PYTHON_CMD=""
LOG_LEVEL="INFO"
INTERACTIVE_MODE=true
DEBUG_MODE=false
SAFE_MODE=false

# ============================================================================
# 颜色和输出配置
# ============================================================================

# 改进的颜色检测函数
setup_colors() {
    # 检查是否支持颜色
    if [[ ! -t 1 ]] || [[ "${NO_COLOR:-}" == "1" ]] || [[ "${TERM:-}" == "dumb" ]]; then
        # 不支持颜色或明确禁用
        RED='' GREEN='' YELLOW='' BLUE='' PURPLE='' CYAN='' WHITE='' BOLD='' DIM='' NC=''
        return 0
    fi

    # 检查终端颜色支持
    local colors=0
    if command -v tput >/dev/null 2>&1; then
        colors=$(tput colors 2>/dev/null || echo 0)
    fi

    if [[ $colors -ge 8 ]]; then
        # 使用tput（更可靠）
        RED=$(tput setaf 1 2>/dev/null || echo '')
        GREEN=$(tput setaf 2 2>/dev/null || echo '')
        YELLOW=$(tput setaf 3 2>/dev/null || echo '')
        BLUE=$(tput setaf 4 2>/dev/null || echo '')
        PURPLE=$(tput setaf 5 2>/dev/null || echo '')
        CYAN=$(tput setaf 6 2>/dev/null || echo '')
        WHITE=$(tput setaf 7 2>/dev/null || echo '')
        BOLD=$(tput bold 2>/dev/null || echo '')
        DIM=$(tput dim 2>/dev/null || echo '')
        NC=$(tput sgr0 2>/dev/null || echo '')
    else
        # 回退到ANSI转义码
        RED='\033[0;31m'
        GREEN='\033[0;32m'
        YELLOW='\033[1;33m'
        BLUE='\033[0;34m'
        PURPLE='\033[0;35m'
        CYAN='\033[0;36m'
        WHITE='\033[1;37m'
        BOLD='\033[1m'
        DIM='\033[2m'
        NC='\033[0m'
    fi
}

# 初始化颜色
setup_colors

# ============================================================================
# 日志和输出函数
# ============================================================================

# 改进的日志函数
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        ERROR)
            echo -e "${RED}[ERROR]${NC} ${timestamp} $message" >&2
            ;;
        WARN|WARNING)
            echo -e "${YELLOW}[WARN]${NC} ${timestamp} $message" >&2
            ;;
        INFO)
            echo -e "${CYAN}[INFO]${NC} ${timestamp} $message"
            ;;
        DEBUG)
            [[ "$DEBUG_MODE" == "true" ]] && echo -e "${DIM}[DEBUG]${NC} ${timestamp} $message"
            ;;
        SUCCESS)
            echo -e "${GREEN}[SUCCESS]${NC} ${timestamp} $message"
            ;;
        *)
            echo -e "[${level}] ${timestamp} $message"
            ;;
    esac
}

# 状态消息函数
status() { log "INFO" "$@"; }
success() { log "SUCCESS" "$@"; }
warn() { log "WARN" "$@"; }
error() { log "ERROR" "$@"; }
debug() { log "DEBUG" "$@"; }

# 用户交互函数
print_header() {
    local title="$1"
    local width=60
    local padding=$(( (width - ${#title}) / 2 ))
    
    echo
    echo -e "${BLUE}$(printf '=%.0s' $(seq 1 $width))${NC}"
    echo -e "${BOLD}$(printf '%*s%s' $padding '' "$title")${NC}"
    echo -e "${BLUE}$(printf '=%.0s' $(seq 1 $width))${NC}"
    echo
}

print_separator() {
    echo -e "${BLUE}$(printf '=%.0s' $(seq 1 60))${NC}"
}

# ============================================================================
# 错误处理和清理函数
# ============================================================================

# 错误处理函数
handle_error() {
    local exit_code=$?
    local line_number=${1:-$LINENO}
    local bash_lineno=${2:-$BASH_LINENO}
    local last_command=${3:-$BASH_COMMAND}
    local funcstack=("${FUNCNAME[@]}")
    
    error "脚本在第 $line_number 行发生错误"
    error "命令: $last_command"
    error "退出码: $exit_code"
    
    if [[ "$DEBUG_MODE" == "true" ]]; then
        error "调用栈:"
        local i
        for (( i=1; i<${#funcstack[@]}; i++ )); do
            error "  $i: ${funcstack[$i]}"
        done
    fi
    
    cleanup_on_exit $exit_code
}

# 设置错误处理
trap 'handle_error $LINENO $BASH_LINENO "$BASH_COMMAND"' ERR

# 信号处理函数
handle_signal() {
    local signal=$1
    warn "收到信号: $signal"
    case $signal in
        INT|TERM)
            warn "用户中断或终止信号，正在清理..."
            cleanup_on_exit 130
            ;;
        HUP)
            warn "终端断开，正在保存状态..."
            cleanup_on_exit 129
            ;;
    esac
}

# 设置信号处理
trap 'handle_signal INT' INT
trap 'handle_signal TERM' TERM
trap 'handle_signal HUP' HUP

# 清理函数
cleanup_on_exit() {
    local exit_code=${1:-0}
    
    debug "开始清理，退出码: $exit_code"
    
    # 移除锁文件
    if [[ -f "$LOCK_FILE" ]]; then
        rm -f "$LOCK_FILE" 2>/dev/null || true
    fi
    
    # 移除PID文件
    if [[ -f "$PID_FILE" ]]; then
        rm -f "$PID_FILE" 2>/dev/null || true
    fi
    
    # 如果是异常退出，显示帮助信息
    if [[ $exit_code -ne 0 ]] && [[ $exit_code -ne 130 ]]; then
        echo
        echo -e "${YELLOW}如果遇到问题：${NC}"
        echo "1. 使用调试模式运行: $0 --debug"
        echo "2. 查看日志文件: $SCRIPT_DIR/update_vcp_logs/"
        echo "3. 运行环境检查: 选择菜单中的 [T] 选项"
        echo
    fi
    
    debug "清理完成"
    exit $exit_code
}

# ============================================================================
# 实用函数
# ============================================================================

# 改进的read函数，支持超时和验证
safe_read() {
    local prompt="$1"
    local var_name="${2:-REPLY}"
    local timeout="${3:-0}"
    local validator="${4:-}"
    local default_value="${5:-}"
    
    local input=""
    local attempts=0
    local max_attempts=3
    
    while [[ $attempts -lt $max_attempts ]]; do
        # 显示提示符
        if [[ -n "$default_value" ]]; then
            echo -n "${prompt} [默认: $default_value]: "
        else
            echo -n "$prompt"
        fi
        
        # 读取输入
        if [[ $timeout -gt 0 ]]; then
            if ! read -r -t "$timeout" input; then
                echo
                warn "输入超时"
                if [[ -n "$default_value" ]]; then
                    input="$default_value"
                else
                    return 1
                fi
            fi
        else
            read -r input
        fi
        
        # 使用默认值（如果输入为空）
        if [[ -z "$input" && -n "$default_value" ]]; then
            input="$default_value"
        fi
        
        # 验证输入
        if [[ -n "$validator" ]]; then
            if eval "$validator \"\$input\""; then
                break
            else
                ((attempts++))
                error "输入无效，请重试 ($attempts/$max_attempts)"
                continue
            fi
        else
            break
        fi
    done
    
    if [[ $attempts -ge $max_attempts ]]; then
        error "输入尝试次数超限"
        return 1
    fi
    
    # 设置变量值
    if [[ "$var_name" != "REPLY" ]]; then
        printf -v "$var_name" '%s' "$input"
    else
        REPLY="$input"
    fi
    
    return 0
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查文件是否存在且可读
file_readable() {
    [[ -f "$1" && -r "$1" ]]
}

# 检查目录是否存在且可写
dir_writable() {
    [[ -d "$1" && -w "$1" ]]
}

# 安全的文件创建
safe_create_file() {
    local file="$1"
    local content="${2:-}"
    
    # 确保目录存在
    local dir
    dir="$(dirname "$file")"
    if ! mkdir -p "$dir" 2>/dev/null; then
        error "无法创建目录: $dir"
        return 1
    fi
    
    # 创建文件
    if ! echo "$content" > "$file" 2>/dev/null; then
        error "无法创建文件: $file"
        return 1
    fi
    
    return 0
}

# 版本比较函数
version_compare() {
    local version1="$1"
    local version2="$2"
    local operator="${3:-eq}"
    
    # 移除非数字字符，保留点号
    version1=$(echo "$version1" | sed 's/[^0-9.]//g')
    version2=$(echo "$version2" | sed 's/[^0-9.]//g')
    
    # 使用sort进行版本比较
    case "$operator" in
        "eq"|"=")
            [[ "$version1" == "$version2" ]]
            ;;
        "ne"|"!=")
            [[ "$version1" != "$version2" ]]
            ;;
        "lt"|"<")
            [[ "$(printf '%s\n' "$version1" "$version2" | sort -V | head -n1)" == "$version1" && "$version1" != "$version2" ]]
            ;;
        "le"|"<=")
            [[ "$(printf '%s\n' "$version1" "$version2" | sort -V | head -n1)" == "$version1" ]]
            ;;
        "gt"|">")
            [[ "$(printf '%s\n' "$version1" "$version2" | sort -V | tail -n1)" == "$version1" && "$version1" != "$version2" ]]
            ;;
        "ge"|">=")
            [[ "$(printf '%s\n' "$version1" "$version2" | sort -V | tail -n1)" == "$version1" ]]
            ;;
        *)
            error "无效的比较操作符: $operator"
            return 1
            ;;
    esac
}

# ============================================================================
# 系统检查和初始化函数
# ============================================================================

# 检查系统兼容性
check_system_compatibility() {
    debug "检查系统兼容性..."
    
    case "$OS_TYPE" in
        "Linux")
            status "检测到 Linux 系统"
            ;;
        "Darwin")
            status "检测到 macOS 系统"
            ;;
        "FreeBSD"|"OpenBSD"|"NetBSD")
            warn "检测到 BSD 系统，脚本可能需要调整"
            ;;
        "CYGWIN"*|"MINGW"*|"MSYS"*)
            warn "检测到 Windows 子系统，建议使用 update_vcp.bat"
            ;;
        *)
            warn "未知操作系统: $OS_TYPE，脚本可能无法正常工作"
            safe_read "是否继续？(y/N): " continue_anyway "" "" 'validate_yes_no' "n"
            if [[ "${continue_anyway,,}" != "y" ]]; then
                error "用户选择退出"
                exit 1
            fi
            ;;
    esac
}

# 验证yes/no输入
validate_yes_no() {
    local input="$1"
    [[ "${input,,}" =~ ^(y|yes|n|no)$ ]]
}

# 验证项目名称
validate_project_name() {
    local input="$1"
    [[ "${input,,}" =~ ^(all|chat|vcpchat|toolbox|tb|vcptoolbox)$ ]]
}

# 检查运行权限
check_permissions() {
    debug "检查运行权限..."
    
    # 检查脚本目录权限
    if ! dir_writable "$SCRIPT_DIR"; then
        error "脚本目录不可写: $SCRIPT_DIR"
        return 1
    fi
    
    # 检查VCP根目录权限
    if [[ -d "$VCP_ROOT" ]] && ! dir_writable "$VCP_ROOT"; then
        warn "VCP根目录不可写: $VCP_ROOT，某些操作可能失败"
    fi
    
    # 检查是否以root运行（可选警告）
    if [[ $EUID -eq 0 ]]; then
        warn "正在以root权限运行脚本"
        warn "建议以普通用户权限运行，除非必要"
        safe_read "是否继续？(y/N): " continue_root "" "" 'validate_yes_no' "n"
        if [[ "${continue_root,,}" != "y" ]]; then
            status "用户选择退出"
            exit 0
        fi
    fi
    
    return 0
}

# 检查并创建锁文件
check_lock_file() {
    debug "检查锁文件..."
    
    if [[ -f "$LOCK_FILE" ]]; then
        local lock_pid
        lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        
        if [[ -n "$lock_pid" ]] && kill -0 "$lock_pid" 2>/dev/null; then
            error "另一个 VCP 更新进程正在运行 (PID: $lock_pid)"
            error "如果确认没有其他进程在运行，请删除锁文件: $LOCK_FILE"
            return 1
        else
            warn "发现陈旧的锁文件，正在清理..."
            rm -f "$LOCK_FILE"
        fi
    fi
    
    # 创建锁文件
    echo $$ > "$LOCK_FILE" || {
        error "无法创建锁文件: $LOCK_FILE"
        return 1
    }
    
    # 创建PID文件
    echo $$ > "$PID_FILE" || {
        warn "无法创建PID文件: $PID_FILE"
    }
    
    debug "锁文件创建成功"
    return 0
}

# 检查必要文件
check_required_files() {
    debug "检查必要文件..."
    
    local required_files=("update_vcp.py")
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if ! file_readable "$SCRIPT_DIR/$file"; then
            missing_files+=("$file")
        fi
    done
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        error "缺少必要文件:"
        for file in "${missing_files[@]}"; do
            error "  - $file"
        done
        error "请确保所有文件位于 VCPUpdate 目录"
        return 1
    fi
    
    status "必要文件检查通过"
    return 0
}

# ============================================================================
# Python环境检查
# ============================================================================

# 改进的Python检查
check_python() {
    debug "检查Python环境..."
    
    local python_candidates=()
    local min_version="3.7"
    
    # 根据系统类型设置候选命令
    case "$OS_TYPE" in
        "Darwin")
            python_candidates=("python3" "python" "/usr/local/bin/python3" "/opt/homebrew/bin/python3")
            ;;
        "Linux")
            python_candidates=("python3" "python" "/usr/bin/python3" "/usr/local/bin/python3")
            ;;
        *)
            python_candidates=("python3" "python")
            ;;
    esac
    
    # 添加更多版本
    for version in 3.12 3.11 3.10 3.9 3.8 3.7; do
        python_candidates+=("python$version")
    done
    
    debug "检查Python候选命令: ${python_candidates[*]}"
    
    for cmd in "${python_candidates[@]}"; do
        if command_exists "$cmd"; then
            debug "检查 $cmd..."
            
            # 获取版本信息
            local version_output
            if version_output=$($cmd --version 2>&1); then
                local version_num
                version_num=$(echo "$version_output" | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -1)
                
                if [[ -n "$version_num" ]]; then
                    debug "发现 Python $version_num: $cmd"
                    
                    # 检查版本是否满足要求
                    if version_compare "$version_num" "$min_version" "ge"; then
                        # 验证关键模块
                        if check_python_modules "$cmd"; then
                            PYTHON_CMD="$cmd"
                            success "使用 Python $version_num: $cmd"
                            return 0
                        else
                            warn "Python $version_num 缺少必要模块: $cmd"
                        fi
                    else
                        debug "Python版本过低 ($version_num < $min_version): $cmd"
                    fi
                fi
            fi
        fi
    done
    
    error "未找到满足要求的Python环境 (需要 Python $min_version+)"
    show_python_install_help
    return 1
}

# 检查Python模块
check_python_modules() {
    local python_cmd="$1"
    local required_modules=("json" "configparser" "subprocess" "threading" "pathlib" "dataclasses")
    
    debug "检查Python模块: ${required_modules[*]}"
    
    for module in "${required_modules[@]}"; do
        if ! "$python_cmd" -c "import $module" >/dev/null 2>&1; then
            debug "缺少模块: $module"
            return 1
        fi
    done
    
    debug "Python模块检查通过"
    return 0
}

# 显示Python安装帮助
show_python_install_help() {
    echo
    echo -e "${YELLOW}Python 安装指南:${NC}"
    
    case "$OS_TYPE" in
        "Darwin")
            echo "  macOS:"
            echo "    brew install python@3"
            echo "    或下载: https://www.python.org/downloads/macos/"
            ;;
        "Linux")
            if command_exists apt; then
                echo "  Ubuntu/Debian:"
                echo "    sudo apt update && sudo apt install python3 python3-pip"
            elif command_exists yum; then
                echo "  CentOS/RHEL:"
                echo "    sudo yum install python3 python3-pip"
            elif command_exists dnf; then
                echo "  Fedora:"
                echo "    sudo dnf install python3 python3-pip"
            elif command_exists pacman; then
                echo "  Arch Linux:"
                echo "    sudo pacman -S python python-pip"
            elif command_exists zypper; then
                echo "  openSUSE:"
                echo "    sudo zypper install python3 python3-pip"
            else
                echo "  Linux:"
                echo "    请使用您的包管理器安装 python3"
            fi
            ;;
        *)
            echo "  请访问: https://www.python.org/downloads/"
            ;;
    esac
    echo
}

# 详细的Python检查
check_python_detailed() {
    print_header "Python 环境详细检查"
    
    if [[ -z "$PYTHON_CMD" ]]; then
        error "Python命令未设置"
        return 1
    fi
    
    # 基本信息
    echo -e "${CYAN}Python 基本信息:${NC}"
    local version_output
    if version_output=$("$PYTHON_CMD" --version 2>&1); then
        echo -e "${GREEN}✓ $version_output${NC}"
    else
        echo -e "${RED}❌ 无法获取Python版本${NC}"
        return 1
    fi
    
    # 检查路径
    local python_path
    if python_path=$("$PYTHON_CMD" -c "import sys; print(sys.executable)" 2>/dev/null); then
        echo -e "${GREEN}✓ Python路径: $python_path${NC}"
    fi
    
    # 检查版本兼容性
    if "$PYTHON_CMD" -c "import sys; exit(0 if sys.version_info >= (3,7) else 1)" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Python版本满足要求 (3.7+)${NC}"
    else
        echo -e "${RED}❌ Python版本过低，需要3.7+${NC}"
        return 1
    fi
    
    # 检查必要模块
    echo -e "${CYAN}检查必要模块:${NC}"
    local modules=("json" "configparser" "subprocess" "threading" "pathlib" "dataclasses")
    local missing_modules=()
    
    for module in "${modules[@]}"; do
        if "$PYTHON_CMD" -c "import $module" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ $module${NC}"
        else
            echo -e "${RED}❌ $module${NC}"
            missing_modules+=("$module")
        fi
    done
    
    if [[ ${#missing_modules[@]} -gt 0 ]]; then
        error "缺少Python模块: ${missing_modules[*]}"
        return 1
    fi
    
    # 检查pip
    echo -e "${CYAN}检查包管理器:${NC}"
    if "$PYTHON_CMD" -m pip --version >/dev/null 2>&1; then
        local pip_version
        pip_version=$("$PYTHON_CMD" -m pip --version 2>/dev/null | cut -d' ' -f2)
        echo -e "${GREEN}✓ pip $pip_version${NC}"
    else
        echo -e "${YELLOW}⚠️  pip 不可用${NC}"
    fi
    
    return 0
}

# ============================================================================
# 菜单和用户界面
# ============================================================================

# 清屏函数
clear_screen() {
    if [[ -t 1 ]]; then
        clear 2>/dev/null || printf '\033[2J\033[H'
    fi
}

# 显示标题
show_title() {
    clear_screen
    print_header "VCP Auto Update Tool $SCRIPT_VERSION"
    
    echo -e "${CYAN}当前目录:${NC} ${DIM}$SCRIPT_DIR${NC}"
    echo -e "${CYAN}VCP根目录:${NC} ${DIM}$VCP_ROOT${NC}"
    echo -e "${CYAN}Python:${NC} ${DIM}$PYTHON_CMD${NC}"
    if [[ "$DEBUG_MODE" == "true" ]]; then
        echo -e "${YELLOW}调试模式:${NC} ${BOLD}已启用${NC}"
    fi
    echo
}

# 显示菜单
show_menu() {
    echo -e "${BOLD}请选择操作：${NC}"
    echo
    echo -e "${CYAN}更新选项:${NC}"
    echo -e "  ${BOLD}[1]${NC} 🚀 并行更新所有项目 ${DIM}(推荐)${NC}"
    echo -e "  ${BOLD}[2]${NC} 🔄 顺序更新所有项目"
    echo -e "  ${BOLD}[3]${NC} 📦 只更新 VCPChat"
    echo -e "  ${BOLD}[4]${NC} 🛠️  只更新 VCPToolBox"
    echo
    echo -e "${CYAN}回滚选项:${NC}"
    echo -e "  ${BOLD}[5]${NC} ⏪ 回滚所有项目"
    echo -e "  ${BOLD}[6]${NC} ⏪ 回滚 VCPChat"
    echo -e "  ${BOLD}[7]${NC} ⏪ 回滚 VCPToolBox"
    echo
    echo -e "${CYAN}检查点选项:${NC}"
    echo -e "  ${BOLD}[8]${NC} 📋 查看检查点列表"
    echo -e "  ${BOLD}[9]${NC} 🔙 恢复到指定检查点"
    echo
    echo -e "${CYAN}管理选项:${NC}"
    echo -e "  ${BOLD}[A]${NC} 📄 查看更新日志"
    echo -e "  ${BOLD}[S]${NC} ℹ️  查看项目状态"
    echo -e "  ${BOLD}[C]${NC} ⚙️  编辑配置文件"
    echo -e "  ${BOLD}[E]${NC} 📤 导出配置模板"
    echo -e "  ${BOLD}[L]${NC} 🧹 清理旧文件"
    echo -e "  ${BOLD}[T]${NC} 🧪 环境检查"
    echo -e "  ${BOLD}[D]${NC} 🐛 调试模式"
    echo -e "  ${BOLD}[H]${NC} ❓ 显示帮助"
    echo -e "  ${BOLD}[0]${NC} 👋 退出"
    echo
}

# ============================================================================
# Python脚本执行函数
# ============================================================================

# 执行Python脚本
run_python_script() {
    local description="$1"
    shift
    
    debug "准备执行Python脚本: $description"
    debug "参数: $*"
    
    # 验证Python命令
    if [[ -z "$PYTHON_CMD" ]]; then
        error "Python命令未设置"
        return 1
    fi
    
    if ! command_exists "$PYTHON_CMD"; then
        error "Python命令不存在: $PYTHON_CMD"
        return 1
    fi
    
    # 验证Python脚本文件
    if ! file_readable "$SCRIPT_DIR/update_vcp.py"; then
        error "Python脚本文件不存在或不可读: $SCRIPT_DIR/update_vcp.py"
        return 1
    fi
    
    print_header "$description"
    
    echo -e "${CYAN}执行命令:${NC} ${DIM}$PYTHON_CMD update_vcp.py $*${NC}"
    echo
    
    # 切换到脚本目录并执行
    local exit_code=0
    (
        cd "$SCRIPT_DIR" || exit 1
        "$PYTHON_CMD" update_vcp.py "$@"
    ) || exit_code=$?
    
    debug "Python脚本执行完成，退出码: $exit_code"
    return $exit_code
}

# 检查执行结果
check_result() {
    local exit_code=$?
    
    echo
    print_separator
    
    if [[ $exit_code -eq 0 ]]; then
        success "操作成功完成！"
        echo
        
        # 显示最新日志位置
        show_latest_log_info
        
        # 显示更新统计
        show_update_stats
    else
        error "操作失败 (退出码: $exit_code)"
        echo
        
        # 显示错误日志位置
        show_latest_log_info "error"
        
        # 显示故障排除信息
        show_troubleshooting_tips
    fi
    
    print_separator
    echo
    
    # 等待用户确认
    safe_read "按回车键继续..." continue_key 30 "" ""
}

# 显示最新日志信息
show_latest_log_info() {
    local log_type="${1:-info}"
    local log_dir="$SCRIPT_DIR/update_vcp_logs"
    
    if [[ -d "$log_dir" ]]; then
        local latest_log
        latest_log=$(find "$log_dir" -name "update_vcp_*.log" -type f -exec ls -t {} + 2>/dev/null | head -1)
        
        if [[ -n "$latest_log" ]]; then
            if [[ "$log_type" == "error" ]]; then
                echo -e "${YELLOW}📋 错误日志: ${DIM}$latest_log${NC}"
            else
                echo -e "${CYAN}💡 最新日志: ${DIM}$latest_log${NC}"
            fi
        fi
    fi
}

# 显示更新统计
show_update_stats() {
    local stats_file="$SCRIPT_DIR/update_vcp_rollback_info.json"
    
    if file_readable "$stats_file"; then
        echo -e "${CYAN}📊 更新统计:${NC}"
        
        # 使用Python安全地读取JSON
        "$PYTHON_CMD" -c "
import json, sys
try:
    with open('$stats_file', 'r', encoding='utf-8') as f:
        data = json.load(f)
        stats = data.get('update_stats', {})
        if stats:
            for k, v in stats.items():
                if v > 0:
                    print(f'  {k}: {v}')
        else:
            print('  暂无统计数据')
except Exception as e:
    print(f'  读取统计数据失败: {e}', file=sys.stderr)
" 2>/dev/null || echo "  无法读取统计数据"
    fi
}

# 显示故障排除提示
show_troubleshooting_tips() {
    echo -e "${CYAN}🔧 常见问题解决方案:${NC}"
    echo "  1. 网络问题: 检查网络连接或配置代理"
    echo "  2. Git 问题: 检查 Git 配置和权限"
    echo "  3. Docker 问题: 确保 Docker 服务正在运行"
    echo "  4. 权限问题: 检查文件和目录权限"
    echo "  5. 配置问题: 检查 update_vcp_config.ini"
    echo "  6. Python 问题: 验证 Python 环境"
    echo
    echo -e "${CYAN}💡 获取更多帮助:${NC}"
    echo "  - 使用调试模式: 选择菜单中的 [D] 选项"
    echo "  - 运行环境检查: 选择菜单中的 [T] 选项"
    echo "  - 查看详细日志: 选择菜单中的 [A] 选项"
}

# ============================================================================
# 菜单操作函数
# ============================================================================

# 确认回滚操作
confirm_rollback() {
    local target="$1"
    local project_param="$2"
    
    clear_screen
    print_header "回滚确认"
    
    echo -e "${YELLOW}⚠️  您确定要回滚 $target 吗？${NC}"
    echo
    echo "此操作将："
    echo "• 撤销最近的更新操作"
    echo "• 恢复到更新前的代码状态"
    echo "• 可能影响配置文件"
    echo
    echo -e "${RED}注意: 此操作不可轻易撤销${NC}"
    echo
    
    safe_read "请输入 'YES' 确认回滚，其他任何输入将取消: " confirm_input
    
    if [[ "$confirm_input" == "YES" ]]; then
        echo
        status "开始回滚 $target..."
        
        if [[ -n "$project_param" ]]; then
            run_python_script "回滚 $target" "--action" "rollback" "--project" "$project_param"
        else
            run_python_script "回滚所有项目" "--action" "rollback"
        fi
        check_result
    else
        echo
        success "已取消回滚操作"
        sleep 2
    fi
}

# 查看日志
view_logs() {
    clear_screen
    print_header "查看更新日志"
    
    local log_dir="$SCRIPT_DIR/update_vcp_logs"
    
    if [[ ! -d "$log_dir" ]]; then
        warn "暂无日志目录"
        echo "请先运行一次更新操作来生成日志"
        echo
        safe_read "按回车键返回..." 
        return
    fi
    
    # 获取日志文件列表（改进的查找方法）
    local logs=()
    while IFS= read -r -d '' log_file; do
        logs+=("$log_file")
    done < <(find "$log_dir" -name "update_vcp_*.log" -type f -print0 2>/dev/null | sort -z -r)
    
    if [[ ${#logs[@]} -eq 0 ]]; then
        warn "暂无日志文件"
        echo
        safe_read "按回车键返回..." 
        return
    fi
    
    # 限制显示数量
    if [[ ${#logs[@]} -gt 10 ]]; then
        logs=("${logs[@]:0:10}")
    fi
    
    echo "最近的日志文件:"
    echo
    
    for i in "${!logs[@]}"; do
        local log_file="${logs[$i]}"
        local log_name
        log_name=$(basename "$log_file")
        local log_size
        log_size=$(du -h "$log_file" 2>/dev/null | cut -f1 || echo "未知")
        local log_time
        log_time=$(stat -c '%y' "$log_file" 2>/dev/null | cut -d' ' -f1,2 | cut -d'.' -f1 || echo "未知时间")
        
        echo "  [$((i+1))] $log_name ${DIM}($log_size, $log_time)${NC}"
    done
    
    echo
    echo "操作选项:"
    echo "  [A] 查看最新日志的最后100行"
    echo "  [F] 查看完整的最新日志"
    echo "  [S] 搜索日志内容"
    echo "  [0] 返回主菜单"
    echo
    
    local log_choice
    safe_read "请选择日志编号 (1-${#logs[@]}) 或操作: " log_choice
    
    case "$log_choice" in
        0)
            return
            ;;
        [Aa])
            show_log_content "${logs[0]}" "tail"
            ;;
        [Ff])
            show_log_content "${logs[0]}" "full"
            ;;
        [Ss])
            search_logs "${logs[@]}"
            ;;
        *)
            if [[ "$log_choice" =~ ^[0-9]+$ ]] && [[ $log_choice -ge 1 && $log_choice -le ${#logs[@]} ]]; then
                show_log_content "${logs[$((log_choice-1))]}" "full"
            else
                error "无效的选择: $log_choice"
                sleep 2
            fi
            ;;
    esac
    
    view_logs  # 递归调用以返回日志选择界面
}

# 显示日志内容
show_log_content() {
    local log_file="$1"
    local view_mode="${2:-full}"
    
    if ! file_readable "$log_file"; then
        error "无法读取日志文件: $log_file"
        sleep 2
        return
    fi
    
    clear_screen
    local log_name
    log_name=$(basename "$log_file")
    print_header "日志内容: $log_name"
    
    case "$view_mode" in
        "tail")
            echo -e "${YELLOW}显示最后100行...${NC}"
            echo
            tail -100 "$log_file" 2>/dev/null || {
                error "无法读取日志文件"
                sleep 2
                return
            }
            ;;
        "full")
            if command_exists less; then
                less "+G" "$log_file"  # +G 跳到文件末尾
            elif command_exists more; then
                more "$log_file"
            else
                echo -e "${YELLOW}显示完整日志...${NC}"
                echo
                cat "$log_file"
            fi
            ;;
    esac
    
    echo
    echo -e "${YELLOW}===== 日志结束 =====${NC}"
    safe_read "按回车键继续..." 
}

# 搜索日志
search_logs() {
    local logs=("$@")
    
    local search_term
    safe_read "请输入搜索关键词: " search_term
    
    if [[ -z "$search_term" ]]; then
        warn "搜索关键词不能为空"
        return
    fi
    
    clear_screen
    print_header "日志搜索结果"
    
    echo -e "${CYAN}搜索关键词: ${BOLD}$search_term${NC}"
    echo
    
    local found_count=0
    for log_file in "${logs[@]}"; do
        if file_readable "$log_file"; then
            local log_name
            log_name=$(basename "$log_file")
            local matches
            matches=$(grep -n -i "$search_term" "$log_file" 2>/dev/null || true)
            
            if [[ -n "$matches" ]]; then
                echo -e "${GREEN}📄 $log_name:${NC}"
                echo "$matches" | head -10  # 限制每个文件最多显示10行
                echo
                ((found_count++))
            fi
        fi
    done
    
    if [[ $found_count -eq 0 ]]; then
        echo -e "${YELLOW}未找到匹配的内容${NC}"
    else
        echo -e "${GREEN}在 $found_count 个日志文件中找到匹配内容${NC}"
    fi
    
    echo
    safe_read "按回车键继续..."
}

# 显示项目状态
show_status() {
    clear_screen
    run_python_script "显示项目状态" "--action" "status"
    echo
    safe_read "按回车键返回..." 
}

# 编辑配置文件
edit_config() {
    clear_screen
    print_header "编辑配置文件"
    
    local config_file="$SCRIPT_DIR/update_vcp_config.ini"
    
    if file_readable "$config_file"; then
        status "正在打开配置文件..."
        
        # 改进的编辑器检测和选择
        local editors=()
        case "$OS_TYPE" in
            "Darwin")
                editors=("code" "nano" "vim" "vi" "subl" "mate")
                ;;
            "Linux")
                editors=("nano" "vim" "vi" "code" "gedit" "kate" "emacs")
                ;;
            *)
                editors=("nano" "vim" "vi")
                ;;
        esac
        
        local editor_found=false
        
        # 检查EDITOR环境变量
        if [[ -n "${EDITOR:-}" ]] && command_exists "$EDITOR"; then
            debug "使用环境变量指定的编辑器: $EDITOR"
            if "$EDITOR" "$config_file"; then
                editor_found=true
            else
                warn "环境变量编辑器执行失败，尝试其他编辑器"
            fi
        fi
        
        # 如果环境变量编辑器失败，尝试其他编辑器
        if [[ "$editor_found" == "false" ]]; then
            for editor in "${editors[@]}"; do
                if command_exists "$editor"; then
                    status "使用 $editor 编辑器"
                    if "$editor" "$config_file"; then
                        editor_found=true
                        break
                    else
                        warn "$editor 执行失败，尝试下一个编辑器"
                    fi
                fi
            done
        fi
        
        # 如果所有编辑器都失败，尝试系统默认
        if [[ "$editor_found" == "false" ]]; then
            case "$OS_TYPE" in
                "Darwin")
                    status "使用系统默认编辑器"
                    if open -t "$config_file" 2>/dev/null; then
                        editor_found=true
                    fi
                    ;;
                "Linux")
                    if [[ -n "${DISPLAY:-}" ]] && command_exists xdg-open; then
                        status "使用系统默认编辑器"
                        if xdg-open "$config_file" 2>/dev/null; then
                            editor_found=true
                        fi
                    fi
                    ;;
            esac
        fi
        
        # 如果仍然失败，显示文件内容
        if [[ "$editor_found" == "false" ]]; then
            warn "未找到合适的编辑器，显示配置文件内容:"
            echo
            echo -e "${CYAN}--- $config_file ---${NC}"
            cat "$config_file"
            echo -e "${CYAN}--- 配置文件结束 ---${NC}"
            echo
            warn "请使用您喜欢的编辑器手动编辑: $config_file"
        else
            success "配置文件编辑完成"
        fi
    else
        warn "配置文件不存在，将在首次运行脚本时自动创建"
        echo
        
        local create_config
        safe_read "是否现在运行状态检查来创建配置文件？(Y/n): " create_config "" "" 'validate_yes_no' "y"
        
        if [[ "${create_config,,}" == "y" ]]; then
            run_python_script "创建配置文件" "--action" "status"
            
            if file_readable "$config_file"; then
                success "配置文件已创建"
                sleep 2
                edit_config  # 递归调用以编辑新创建的文件
                return
            else
                error "配置文件创建失败"
            fi
        fi
    fi
    
    echo
    safe_read "按回车键返回..." 
}

# 导出配置模板
export_config() {
    clear_screen
    run_python_script "导出配置模板" "--action" "export-config"
    
    local template_file="$SCRIPT_DIR/update_vcp_config_template.ini"
    
    if file_readable "$template_file"; then
        echo
        success "配置模板已导出到: $template_file"
        echo
        
        local view_template
        safe_read "是否查看配置模板？(Y/n): " view_template "" "" 'validate_yes_no' "y"
        
        if [[ "${view_template,,}" == "y" ]]; then
            show_log_content "$template_file" "full"
        fi
    fi
    
    echo
    safe_read "按回车键返回..." 
}

# 清理旧文件
cleanup_files() {
    clear_screen
    print_header "清理旧文件"
    
    echo "将清理以下内容："
    echo "• 30天前的日志文件"
    echo "• 过期的备份文件"
    echo "• 临时文件和缓存"
    if command_exists docker; then
        echo "• 未使用的Docker资源（如果可用）"
    fi
    echo
    
    local confirm
    safe_read "确认清理？(Y/n): " confirm "" "" 'validate_yes_no' "y"
    
    if [[ "${confirm,,}" == "y" ]]; then
        echo
        run_python_script "清理旧文件" "--action" "cleanup"
        echo
        success "清理完成"
    else
        echo
        status "已取消清理操作"
    fi
    
    echo
    safe_read "按回车键返回..." 
}

# 环境检查
test_environment() {
    clear_screen
    print_header "环境检查"
    
    # 操作系统信息
    echo -e "${CYAN}操作系统信息:${NC}"
    case "$OS_TYPE" in
        "Darwin")
            local macos_version
            macos_version=$(sw_vers -productVersion 2>/dev/null || echo "未知")
            echo -e "${GREEN}✓ macOS $macos_version${NC}"
            ;;
        "Linux")
            if file_readable "/etc/os-release"; then
                local os_name os_version
                os_name=$(grep '^NAME=' /etc/os-release | cut -d'"' -f2)
                os_version=$(grep '^VERSION=' /etc/os-release | cut -d'"' -f2 || echo "")
                echo -e "${GREEN}✓ $os_name $os_version${NC}"
            else
                echo -e "${GREEN}✓ $OS_TYPE $OS_VERSION${NC}"
            fi
            ;;
        *)
            echo -e "${GREEN}✓ $OS_TYPE $OS_VERSION${NC}"
            ;;
    esac
    
    echo -e "${GREEN}✓ 架构: $ARCH${NC}"
    echo
    
    # Python环境检查
    echo -e "${CYAN}Python 环境检查:${NC}"
    if check_python_detailed; then
        echo -e "${GREEN}✓ Python 环境正常${NC}"
    else
        echo -e "${RED}❌ Python 环境有问题${NC}"
    fi
    echo
    
    # Git检查
    echo -e "${CYAN}Git 环境检查:${NC}"
    check_git_environment
    echo
    
    # Docker检查
    echo -e "${CYAN}Docker 环境检查:${NC}"
    check_docker_environment
    echo
    
    # 项目目录检查
    echo -e "${CYAN}项目目录检查:${NC}"
    check_project_directories
    echo
    
    # VCPUpdate目录检查
    echo -e "${CYAN}VCPUpdate 目录检查:${NC}"
    check_vcpupdate_structure
    echo
    
    # 网络连接检查
    echo -e "${CYAN}网络连接检查:${NC}"
    check_network_connectivity
    echo
    
    success "环境检查完成"
    safe_read "按回车键返回..." 
}

# Git环境检查
check_git_environment() {
    if command_exists git; then
        local git_version
        git_version=$(git --version 2>/dev/null | head -1)
        echo -e "${GREEN}✓ $git_version${NC}"
        
        # 检查Git配置
        local git_user git_email
        git_user=$(git config --global user.name 2>/dev/null || echo "")
        git_email=$(git config --global user.email 2>/dev/null || echo "")
        
        if [[ -n "$git_user" && -n "$git_email" ]]; then
            echo -e "${GREEN}✓ Git用户: $git_user <$git_email>${NC}"
        else
            echo -e "${YELLOW}⚠️  Git用户信息未配置${NC}"
            echo -e "${DIM}   提示: git config --global user.name \"Your Name\"${NC}"
            echo -e "${DIM}   提示: git config --global user.email \"your.email@example.com\"${NC}"
        fi
        
        # 检查SSH配置
        if [[ -f "$HOME/.ssh/id_rsa" || -f "$HOME/.ssh/id_ed25519" ]]; then
            echo -e "${GREEN}✓ SSH密钥已配置${NC}"
        else
            echo -e "${YELLOW}⚠️  未检测到SSH密钥${NC}"
        fi
    else
        echo -e "${RED}❌ Git 未安装或不在 PATH 中${NC}"
        echo -e "${DIM}   下载: https://git-scm.com/download${NC}"
    fi
}

# Docker环境检查
check_docker_environment() {
    if command_exists docker; then
        local docker_version
        docker_version=$(docker --version 2>/dev/null || echo "Docker version check failed")
        echo -e "${GREEN}✓ $docker_version${NC}"
        
        # 检查Docker Compose
        if command_exists docker-compose; then
            local compose_version
            compose_version=$(docker-compose --version 2>/dev/null || echo "Docker Compose version check failed")
            echo -e "${GREEN}✓ $compose_version${NC}"
        elif docker compose version >/dev/null 2>&1; then
            local compose_version
            compose_version=$(docker compose version 2>/dev/null | head -1)
            echo -e "${GREEN}✓ Docker Compose (plugin): $compose_version${NC}"
        else
            echo -e "${YELLOW}⚠️  Docker Compose 未找到${NC}"
        fi
        
        # 检查Docker服务状态
        if docker info >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Docker 服务正在运行${NC}"
            
            # 检查Docker权限
            if docker ps >/dev/null 2>&1; then
                echo -e "${GREEN}✓ Docker 权限正常${NC}"
            else
                echo -e "${YELLOW}⚠️  Docker 权限不足${NC}"
                echo -e "${DIM}   提示: sudo usermod -aG docker \$USER${NC}"
            fi
        else
            echo -e "${YELLOW}⚠️  Docker 服务未运行或权限不足${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Docker 未安装${NC}"
        echo -e "${DIM}   下载: https://www.docker.com/products/docker-desktop${NC}"
    fi
}

# 项目目录检查
check_project_directories() {
    local projects=(
        "VCPChat-main"
        "VCPToolBox-main"
    )
    
    for project in "${projects[@]}"; do
        local project_path="$VCP_ROOT/$project"
        
        if [[ -d "$project_path" ]]; then
            echo -e "${GREEN}✓ $project 目录存在${NC}"
            
            if [[ -d "$project_path/.git" ]]; then
                echo -e "${GREEN}✓ $project 是 Git 仓库${NC}"
            else
                echo -e "${YELLOW}⚠️  $project 不是 Git 仓库${NC}"
            fi
            
            # 特殊检查VCPToolBox的Docker配置
            if [[ "$project" == "VCPToolBox-main" ]]; then
                local compose_files=("docker-compose.yml" "docker-compose.yaml" "compose.yml" "compose.yaml")
                local compose_found=false
                
                for file in "${compose_files[@]}"; do
                    if [[ -f "$project_path/$file" ]]; then
                        echo -e "${GREEN}✓ 找到 Docker Compose 配置: $file${NC}"
                        compose_found=true
                        break
                    fi
                done
                
                if [[ "$compose_found" == "false" ]]; then
                    echo -e "${YELLOW}⚠️  未找到 Docker Compose 配置${NC}"
                fi
            fi
        else
            echo -e "${RED}❌ $project 目录不存在${NC}"
        fi
    done
}

# VCPUpdate目录结构检查
check_vcpupdate_structure() {
    local files_and_dirs=(
        "update_vcp.py:file:Python主脚本"
        "update_vcp.sh:file:Shell脚本"
        "update_vcp.bat:file:Windows批处理"
        "update_vcp_config.ini:file:配置文件"
        "update_vcp_rollback_info.json:file:回滚信息"
        "update_vcp_logs:dir:日志目录"
        "backups:dir:备份目录"
        "__pycache__:dir:Python缓存"
    )
    
    for item in "${files_and_dirs[@]}"; do
        IFS=':' read -ra ITEM_INFO <<< "$item"
        local name="${ITEM_INFO[0]}"
        local type="${ITEM_INFO[1]}"
        local description="${ITEM_INFO[2]}"
        local path="$SCRIPT_DIR/$name"
        
        case "$type" in
            "file")
                if file_readable "$path"; then
                    echo -e "${GREEN}✓ $description ($name)${NC}"
                else
                    echo -e "${CYAN}ℹ️  $description 将在需要时创建${NC}"
                fi
                ;;
            "dir")
                if [[ -d "$path" ]]; then
                    local count=0
                    case "$name" in
                        "update_vcp_logs")
                            count=$(find "$path" -name "update_vcp_*.log" -type f 2>/dev/null | wc -l)
                            echo -e "${GREEN}✓ $description ($count 个日志文件)${NC}"
                            ;;
                        "backups")
                            count=$(find "$path" -name "*.bundle" -type f 2>/dev/null | wc -l)
                            echo -e "${GREEN}✓ $description ($count 个备份)${NC}"
                            ;;
                        *)
                            echo -e "${GREEN}✓ $description${NC}"
                            ;;
                    esac
                else
                    echo -e "${CYAN}ℹ️  $description 将在需要时创建${NC}"
                fi
                ;;
        esac
    done
}

# 网络连接检查
check_network_connectivity() {
    local test_hosts=("github.com" "raw.githubusercontent.com")
    
    for host in "${test_hosts[@]}"; do
        if ping_host "$host"; then
            echo -e "${GREEN}✓ 可以访问 $host${NC}"
        else
            echo -e "${YELLOW}⚠️  无法访问 $host${NC}"
        fi
    done
    
    # DNS检查
    if command_exists nslookup; then
        if nslookup github.com >/dev/null 2>&1; then
            echo -e "${GREEN}✓ DNS 解析正常${NC}"
        else
            echo -e "${YELLOW}⚠️  DNS 解析可能有问题${NC}"
        fi
    fi
}

# Ping主机函数
ping_host() {
    local host="$1"
    local ping_cmd
    
    case "$OS_TYPE" in
        "Darwin")
            ping_cmd="ping -c 1 -t 3"
            ;;
        "Linux")
            ping_cmd="ping -c 1 -W 3"
            ;;
        *)
            ping_cmd="ping -c 1"
            ;;
    esac
    
    $ping_cmd "$host" >/dev/null 2>&1
}

# 查看检查点
list_checkpoints() {
    clear_screen
    run_python_script "查看检查点列表" "--action" "list-checkpoints"
    echo
    safe_read "按回车键返回..." 
}

# 恢复检查点
restore_checkpoint() {
    clear_screen
    print_header "恢复到指定检查点"
    
    echo "首先，让我们查看可用的检查点："
    echo
    
    # 显示检查点列表
    "$PYTHON_CMD" update_vcp.py --action list-checkpoints 2>/dev/null || {
        error "无法获取检查点列表"
        safe_read "按回车键返回..." 
        return
    }
    
    echo
    echo -e "${CYAN}项目别名说明：${NC}"
    echo "• chat / vcpchat → VCPChat"
    echo "• toolbox / tb / vcptoolbox → VCPToolBox"
    echo
    
    local project_choice
    safe_read "请选择项目: " project_choice "" "" 'validate_project_name'
    
    if [[ -z "$project_choice" ]]; then
        warn "项目名称不能为空"
        safe_read "按回车键返回..." 
        return
    fi
    
    # 规范化项目名称
    local project_param
    case "${project_choice,,}" in
        "chat"|"vcpchat"|"vcpchat-main")
            project_param="chat"
            ;;
        "toolbox"|"tb"|"vcptoolbox"|"vcptoolbox-main")
            project_param="toolbox"
            ;;
        *)
            error "无效的项目选择: $project_choice"
            echo -e "${CYAN}可用项目: chat, vcpchat, toolbox, tb, vcptoolbox${NC}"
            safe_read "按回车键返回..." 
            return
            ;;
    esac
    
    local checkpoint_name
    safe_read "请输入检查点名称: " checkpoint_name
    
    if [[ -z "$checkpoint_name" ]]; then
        error "检查点名称不能为空"
        safe_read "按回车键返回..." 
        return
    fi
    
    echo
    status "恢复 $project_choice 到检查点: $checkpoint_name"
    echo
    
    run_python_script "恢复检查点" "--action" "checkpoint" "--project" "$project_param" "--checkpoint" "$checkpoint_name"
    check_result
}

# 调试模式
debug_mode() {
    clear_screen
    print_header "调试模式"
    
    echo "将以调试模式运行脚本，显示详细的执行信息"
    echo
    echo "请选择操作:"
    echo "  [1] 状态检查 (调试模式)"
    echo "  [2] 更新项目 (调试模式)"
    echo "  [3] 回滚项目 (调试模式)"
    echo "  [4] 自定义调试命令"
    echo "  [0] 返回主菜单"
    echo
    
    local debug_choice
    safe_read "请选择: " debug_choice
    
    case "$debug_choice" in
        1)
            run_python_script "状态检查 (调试模式)" "--action" "status" "--debug"
            ;;
        2)
            echo
            local debug_project
            safe_read "更新哪个项目？(all/chat/toolbox): " debug_project "" "" 'validate_project_name'
            
            case "${debug_project,,}" in
                "all")
                    run_python_script "更新所有项目 (调试模式)" "--debug"
                    ;;
                "chat"|"vcpchat")
                    run_python_script "更新 VCPChat (调试模式)" "--project" "chat" "--debug"
                    ;;
                "toolbox"|"tb"|"vcptoolbox")
                    run_python_script "更新 VCPToolBox (调试模式)" "--project" "toolbox" "--debug"
                    ;;
                *)
                    error "无效的项目选择: $debug_project"
                    safe_read "按回车键返回..." 
                    return
                    ;;
            esac
            ;;
        3)
            echo
            local debug_project
            safe_read "回滚哪个项目？(all/chat/toolbox): " debug_project "" "" 'validate_project_name'
            
            case "${debug_project,,}" in
                "all")
                    run_python_script "回滚所有项目 (调试模式)" "--action" "rollback" "--debug"
                    ;;
                "chat"|"vcpchat")
                    run_python_script "回滚 VCPChat (调试模式)" "--action" "rollback" "--project" "chat" "--debug"
                    ;;
                "toolbox"|"tb"|"vcptoolbox")
                    run_python_script "回滚 VCPToolBox (调试模式)" "--action" "rollback" "--project" "toolbox" "--debug"
                    ;;
                *)
                    error "无效的项目选择: $debug_project"
                    safe_read "按回车键返回..." 
                    return
                    ;;
            esac
            ;;
        4)
            echo
            echo "示例调试命令:"
            echo "  --action status --debug"
            echo "  --project chat --debug"
            echo "  --action list-checkpoints --debug"
            echo
            
            local custom_args
            safe_read "输入自定义命令参数: " custom_args
            
            if [[ -n "$custom_args" ]]; then
                # 安全地解析参数
                local args_array
                read -ra args_array <<< "$custom_args"
                run_python_script "自定义调试命令" "${args_array[@]}"
            fi
            ;;
        0)
            return
            ;;
        *)
            error "无效的选择"
            sleep 2
            return
            ;;
    esac
    
    echo
    safe_read "按回车键继续..."
}

# 显示帮助
show_help() {
    clear_screen
    print_header "使用帮助和说明"
    
    echo -e "${CYAN}🚀 更新功能：${NC}"
    echo "   选项 1-4：不同的更新模式"
    echo "   • 并行更新：多个项目同时更新（推荐，速度快）"
    echo "   • 顺序更新：一个接一个更新项目（稳定，易调试）"
    echo "   • 单项目更新：只更新指定的项目"
    echo
    echo -e "${CYAN}⏪ 回滚功能：${NC}"
    echo "   选项 5-7：撤销最近的更新"
    echo "   • 回滚前需要输入 'YES' 确认操作"
    echo "   • 恢复到更新前的代码和配置状态"
    echo "   • 支持单个项目或全部项目回滚"
    echo
    echo -e "${CYAN}📋 检查点功能：${NC}"
    echo "   选项 8：查看所有可用的Git检查点"
    echo "   选项 9：恢复到指定的检查点"
    echo "   • 检查点类型：before_update, after_fetch, after_merge等"
    echo "   • 提供比回滚更精细的控制"
    echo
    echo -e "${CYAN}📄 日志和状态：${NC}"
    echo "   选项 A：查看详细的更新日志"
    echo "   选项 S：显示当前项目状态"
    echo "   • 支持日志搜索和分页查看"
    echo "   • 显示项目健康状态和配置信息"
    echo
    echo -e "${CYAN}⚙️  配置管理：${NC}"
    echo "   选项 C：编辑配置文件"
    echo "   选项 E：导出配置模板"
    echo "   • 自定义更新行为和项目设置"
    echo "   • 支持多种编辑器自动检测"
    echo
    echo -e "${CYAN}🧹 维护功能：${NC}"
    echo "   选项 L：清理旧日志和备份文件"
    echo "   选项 T：全面的环境配置检查"
    echo "   选项 D：调试模式执行和问题诊断"
    echo
    echo -e "${CYAN}💡 使用提示：${NC}"
    echo "   • 项目别名：chat=VCPChat, toolbox=VCPToolBox"
    echo "   • 所有运行时文件保存在VCPUpdate目录"
    echo "   • 首次使用建议运行环境检查（选项 T）"
    echo "   • 遇到问题时使用调试模式（选项 D）"
    echo "   • 更新前会自动创建备份和检查点"
    echo "   • 支持并行和顺序两种更新模式"
    echo
    echo -e "${CYAN}📁 目录结构：${NC}"
    echo "   VCP/"
    echo "   ├── VCPChat-main/              (VCPChat 项目)"
    echo "   ├── VCPToolBox-main/           (VCPToolBox 项目)"
    echo "   └── VCPUpdate/                 (更新工具目录)"
    echo "       ├── update_vcp.py          (主 Python 脚本)"
    echo "       ├── update_vcp.sh          (本 Shell 脚本)"
    echo "       ├── update_vcp.bat         (Windows 批处理)"
    echo "       ├── update_vcp_config.ini  (配置文件)"
    echo "       ├── update_vcp_rollback_info.json (回滚数据)"
    echo "       ├── update_vcp_logs/       (日志目录)"
    echo "       └── backups/               (备份目录)"
    echo
    echo -e "${CYAN}📋 系统需求：${NC}"
    echo "   • Python 3.7+ (推荐 3.9+)"
    echo "   • Git 2.20+ (推荐最新版本)"
    echo "   • Docker (可选，用于 VCPToolBox)"
    echo "   • 网络连接（用于同步更新）"
    echo "   • 磁盘空间至少 1GB"
    echo
    echo -e "${CYAN}🔧 故障排除：${NC}"
    echo "   • 权限问题：检查文件和目录权限，必要时使用sudo"
    echo "   • 网络问题：检查防火墙、代理设置或DNS配置"
    echo "   • Git问题：验证Git配置、SSH密钥和远程仓库访问"
    echo "   • Docker问题：确保Docker服务运行且用户在docker组"
    echo "   • Python问题：验证Python版本和必要模块安装"
    echo "   • 配置问题：检查并重新生成配置文件"
    echo
    echo -e "${CYAN}🆘 获取帮助：${NC}"
    echo "   • 使用调试模式 [D] 获取详细错误信息"
    echo "   • 运行环境检查 [T] 诊断系统问题"
    echo "   • 查看日志文件 [A] 了解具体错误"
    echo "   • 访问项目主页获取最新文档和支持"
    echo
    safe_read "按回车键返回..." 
}

# ============================================================================
# 主函数和流程控制
# ============================================================================

# 程序初始化
initialize() {
    debug "开始初始化..."
    
    # 检查系统兼容性
    check_system_compatibility
    
    # 检查运行权限
    check_permissions
    
    # 检查锁文件
    check_lock_file
    
    # 检查必要文件
    check_required_files
    
    # 检查Python环境
    check_python
    
    debug "初始化完成"
}

# 处理命令行参数
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --debug)
                DEBUG_MODE=true
                debug "调试模式已启用"
                ;;
            --safe)
                SAFE_MODE=true
                debug "安全模式已启用"
                ;;
            --non-interactive)
                INTERACTIVE_MODE=false
                debug "非交互模式已启用"
                ;;
            --no-color)
                NO_COLOR=1
                setup_colors  # 重新设置颜色
                ;;
            --help|-h)
                show_help_and_exit
                ;;
            --version|-v)
                echo "VCP Auto Update Tool $SCRIPT_VERSION"
                exit 0
                ;;
            *)
                warn "未知参数: $1"
                ;;
        esac
        shift
    done
}

# 显示帮助并退出
show_help_and_exit() {
    echo "VCP Auto Update Tool $SCRIPT_VERSION"
    echo
    echo "用法: $SCRIPT_NAME [选项]"
    echo
    echo "选项:"
    echo "  --debug              启用调试模式"
    echo "  --safe               启用安全模式"
    echo "  --non-interactive    非交互模式"
    echo "  --no-color           禁用颜色输出"
    echo "  --help, -h           显示帮助信息"
    echo "  --version, -v        显示版本信息"
    echo
    echo "示例:"
    echo "  $SCRIPT_NAME                 # 启动交互式菜单"
    echo "  $SCRIPT_NAME --debug         # 以调试模式启动"
    echo "  $SCRIPT_NAME --no-color      # 禁用颜色输出"
    echo
    exit 0
}

# 主菜单循环
main_menu_loop() {
    while true; do
        show_title
        show_menu
        
        local choice
        safe_read "请输入选项: " choice 60
        
        case "$choice" in
            1)
                clear_screen
                run_python_script "并行更新所有 VCP 项目" "--parallel"
                check_result
                ;;
            2)
                clear_screen
                run_python_script "顺序更新所有 VCP 项目" "--sequential"
                check_result
                ;;
            3)
                clear_screen
                run_python_script "更新 VCPChat" "--project" "chat"
                check_result
                ;;
            4)
                clear_screen
                run_python_script "更新 VCPToolBox" "--project" "toolbox"
                check_result
                ;;
            5)
                confirm_rollback "所有项目" ""
                ;;
            6)
                confirm_rollback "VCPChat" "chat"
                ;;
            7)
                confirm_rollback "VCPToolBox" "toolbox"
                ;;
            8)
                list_checkpoints
                ;;
            9)
                restore_checkpoint
                ;;
            [Aa])
                view_logs
                ;;
            [Ss])
                show_status
                ;;
            [Cc])
                edit_config
                ;;
            [Ee])
                export_config
                ;;
            [Ll])
                cleanup_files
                ;;
            [Tt])
                test_environment
                ;;
            [Dd])
                debug_mode
                ;;
            [Hh])
                show_help
                ;;
            0)
                exit_gracefully
                ;;
            "")
                warn "请输入一个选项"
                sleep 1
                ;;
            *)
                error "无效的选择: $choice"
                warn "请输入有效的选项 (0-9, A-H)"
                sleep 2
                ;;
        esac
    done
}

# 优雅退出
exit_gracefully() {
    clear_screen
    print_header "感谢使用 VCP Auto Update Tool $SCRIPT_VERSION"
    
    echo "项目信息:"
    echo "• VCPChat: https://github.com/lioensky/VCPChat"
    echo "• VCPToolBox: https://github.com/lioensky/VCPToolBox"
    echo
    echo "支持和反馈:"
    echo "• 如有问题或建议，欢迎在 GitHub 上提交 Issue"
    echo "• 感谢您的使用和支持！"
    echo
    
    status "正在清理临时文件..."
    cleanup_on_exit 0
}

# ============================================================================
# 主程序入口
# ============================================================================

main() {
    # 解析命令行参数
    parse_arguments "$@"
    
    # 程序初始化
    initialize
    
    # 显示启动信息
    if [[ "$DEBUG_MODE" == "true" ]]; then
        debug "VCP Auto Update Tool $SCRIPT_VERSION 启动"
        debug "脚本目录: $SCRIPT_DIR"
        debug "VCP根目录: $VCP_ROOT"
        debug "Python命令: $PYTHON_CMD"
        debug "操作系统: $OS_TYPE $OS_VERSION"
        debug "架构: $ARCH"
    fi
    
    # 启动主菜单循环
    main_menu_loop
}

# 只有在直接执行脚本时才运行main函数
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi