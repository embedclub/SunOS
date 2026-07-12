# add env

`先写设计文档，再编程` 


# 进程管理
## 什么是进程(process)
在 Linux 系统中：触发任何一个事件事，系统都会将它定义成一个进程，并且给予这个进程一个 ID，称为 PID，同时依据启发这个进程的用户与相关属性关系，给予这个 PID 一组有效的权限设置。
## 进程与程序 （process & program）
- 程序 program：通常为 binary program，实体文件的形态存在
- 进程 process：程序被触发后，执行者的权限与属性、程序的程序代码与所需数据等都会被加载到内存中，操作系统并给予这个内存单元一个标识符（PID），可以说，进程就是一个正在运行的程序

## 子进程与父进程
我们登陆到 bash，该 bash 是一个程序，并有一个 PID，在这个 bash 上执行指令，触发了相关指令的程序运行，从而得到该程序的 PID，这个 PID 就是一个子进程，原本的 bash 就是一个父进程

下面以一个小练习，来了解什么是子进程/父进程
```
# 在目前的 bash 环境下，再触发一次 bash，并以 ps -l 指令管擦进程相关的输出信息
# 直接执行 bash 指令，会进入到子进程的环境中
[root@study ~]# bash
[root@study ~]# ps -l
F S   UID   PID  PPID  C PRI  NI ADDR SZ WCHAN  TTY          TIME CMD
4 S     0  5713  1923  0  80   0 - 32064 do_wai pts/0    00:00:00 su
4 S     0  5862  5713  0  80   0 - 29218 do_wai pts/0    00:00:00 bash
4 S     0 10917  5862  0  80   0 -  3184 do_wai pts/0    00:00:00 bash
0 R     0 11193 10917  0  80   0 - 12407 -      pts/0    00:00:00 ps
# 注意 PID 与 PPID，第 1 行的 PID 与第 2 行的 PPID 是一样的
# 第 2 行的 CMD 是 bash，就是从第一行中执行 bash 产生出来的
```

# 内存管理

 [前辈经验](https://github.com/0voice/kernel_memory_management)

# 文件系统

# 设备驱动

# 用户接口

# 系统调用
