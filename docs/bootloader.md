#add env 
## linux-4.0
sudo apt-get install qemu libncurses5-dev
sudo apt-get install build-essential gcc-5-aarch64-linux-gnu
cd /usr/bin/
sudo ln -s aarch64-linux-gnu-gcc-5 aarch64-linux-gnu-gcc

## add asop
https://mirrors.tuna.tsinghua.edu.cn/help/AOSP/

## git clone linux 

git clone https://github.com/torvalds/linux.git -b linux-4.0


1. Bootloader 引导
当我们按下手机的电源键时，首先会运行bootloader，bootloader的主要作用是初始化基本的硬件设备（例如 CPU 内存 Flash等），并且建立空间映射。目的是为装载Linux内核做好准备，在Linux内核装载完毕后，bootloader会被移除。
在bootloader的运行期间，用户可以通过规定好的组合键，可以进入系统的两个模块
- Fastboot 这个模式可以让用户快速升级指定的分区，是Android设计的一套通过USB来更新分区的协议
- Recovery 模式是Android特有的系统升级，利用Recovery模式，系统可以恢复出厂设置，或者执行OTA、升级补丁和固件升级
2. 装载和启动Linux内核
Android的 boot.img 存放的就是Linux内核和一个根文件系统。boot.img会被bootloader装载进内存，然后Linux内核会进行整个系统的初始化，最后启动init进程
3. 启动init进程
Linux内核加载完成后，会首先启动init进程，init进程是第一个进程。在init进程启动时，会解析Linux的脚本配置文件init.rc文件。根据配置文件的内容，init进程会装载Android的系统文件系统、创建系统目录、初始化系统属性，启动Android系统重要的守护进程（USB守护进程、adb守护进程、void守护进程、rild守护进程）
4. 启动ServerManager
ServerManager由init进程启动。它主要的作用是管理Binder服务，负责binder的注册服务。
5. 启动Zygote进程
Init进程初始化结束时，会启动Zygote进程，Zygote进程会fork出应用程序，是所有应用程序的父进程，Zygote进程在初始化时会创建Dalivik虚拟机、预装载系统资源文件和Java类。所有从Zygote进程fork出的用户进程都会集成和共享这些资源
6.启动SystemServer
SystemServer是Zygote进程fork出的第一个进程，也是整个系统的核心进程。在SystemServer中运行着Android系统大部分的Binder服务。SystemServer首先启动本地服务SensorService，紧接着启动包括 ActivityManagerService等。
7. 启动MediaServer
MediaServer由init进程启动。它包含了多媒体相关的本地服务。
8. 启动Luancher
