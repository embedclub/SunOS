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
