# 如何确认我的系统glibc版本？
## 使用`ldd --version`命令

```shell
ldd --version
```

# 准备环境与下载glibc源码
## 安装必须的编译工具链
以Ubuntu系统为例

```
sudo apt-get install build-essential gawk bison python3 -y
```
创建独立的源码编译工作目录
```
mkdir ~/glibc_debug && cd ~/glibc_debug
wget http://ftp.gnu.org/gnu/libc/glibc-2.35.tar.gz
tar -xzf glibc-2.35.tar.gz
```

# 配置并编译 glibc
**注意：** `glibc`强烈禁止在源码根目录下直接编译，必须创建一个独立的`build`目录。
```
cd glibc-2.35
mkdir build && cd build

# 配置编译选项：
# --prefix 指定安装到我们自定义的目录，绝对不要覆盖系统默认的 /usr
# --enable-debug 开启调试信息，方便后续 GDB 调试
../configure --prefix=$HOME/glibc_debug/install --enable-debug=yes

# 开始编译（根据你的CPU核心数调整 -j 后面的数字，加快编译速度）
make -j$(nproc)

# 安装到指定的 prefix 目录
make install
```
编译完成后，定制版 glibc 就会安静地躺在 $HOME/glibc_debug/install 目录下，包含 lib/libc.so.6 等核心文件。

# 编写测试代码
写一段简单的 C 语言代码（test_malloc.c），用来触发 malloc 和 free 的操作：
```C++
#include <stdio.h>
#include <stdlib.h>

int main() {
    printf("=== 开始调试 malloc 系统调用 ===\n");
    
    // 1. 分配一个小内存（预期触发 brk/sbrk）
    printf("正在分配 64 字节的小内存...\n");
    void *small_ptr = malloc(64);
    if (small_ptr) printf("小内存分配成功: %p\n\n", small_ptr);
    
    // 2. 分配一个大内存（预期触发 mmap，默认阈值为 128KB）
    printf("正在分配 200KB 的大内存...\n");
    void *large_ptr = malloc(200 * 1024); 
    if (large_ptr) printf("大内存分配成功: %p\n\n", large_ptr);
    
    free(small_ptr);
    free(large_ptr);
    return 0;
}
```
编译这段代码（记得加上 -g 参数保留调试符号）：
```shell
gcc -g test_malloc.c -o test_malloc
```

# 使用 GDB 调试自定义 glibc 中的 malloc
结合 GDB 使用时，可以在 GDB 里这样启动：
```
(gdb) file ./test_malloc
(gdb) set args --library-path $HOME/glibc_debug/install/lib ./test_malloc
(gdb) set environment LD_PRELOAD $HOME/glibc_debug/install/lib/libc.so
(gdb) break malloc
(gdb) run
```

# 使用 patchelf 修改程序链接的glibc版本

## 编译并安装指定版本的 glibc
### 下载并解压源码：
```
mkdir ~/glibc_debug && cd ~/glibc_debug
wget http://ftp.gnu.org/gnu/libc/glibc-2.35.tar.gz
tar -xzf glibc-2.35.tar.gz
```
### 创建构建目录并配置：
```
cd glibc-2.35
mkdir glibc-2.35-build && cd glibc-2.35-build
../glibc-2.35/configure --prefix=/opt/glibc-2.35
```
### 编译并安装：
```
make -j$(nproc)
sudo make install
```
## 使用 patchelf 修改目标程序
### 安装 patchelf：
```
sudo apt install patchelf
```
### 修改主程序（如 0dcloud）：
```
patchelf --set-interpreter /opt/glibc-2.35/lib/ld-linux-x86-64.so.2 \
         --set-rpath /opt/glibc-2.35/lib \
         ./0dcloud
```
### 修改依赖插件（如 libsqlite3_flutter_libs_plugin.so）：
由于你的程序依赖该插件，插件本身也需要链接到新版 glibc，否则依然会报错：
```
patchelf --set-rpath /opt/glibc-2.35/lib \
         /usr/share/0dcloud/lib/libsqlite3_flutter_libs_plugin.so
```

### 运行程序
修改完成后，直接运行程序即可。为了让系统优先加载自定义的库，建议在运行时加上 LD_LIBRARY_PATH 环境变量：
```
LD_LIBRARY_PATH=/opt/glibc-2.34/lib ./0dcloud
```
