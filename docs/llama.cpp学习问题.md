# 问题一
为什么在common_init_from_params函数里面就会调用加载模型文件函数？

# debug参数配置如下，-n的含义是什么？
"-m", "Qwen3.5-0.8B-Q4_K_M.gguf",
"-p", "Hello, my name is",
"-n", "128"
-n 控制单次生成的最大 token 数

