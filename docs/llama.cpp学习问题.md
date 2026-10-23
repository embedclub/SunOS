# 问题一：为什么在common_init_from_params函数里面就会调用加载模型文件函数？
  因为模型涉及的上下文，单词推理tokens数量都是在参数里面传递的？所以需要根据参数解析结果，加载模型文件，配置不同参数。

# 问题二：debug参数配置如下，-n的含义是什么？
"-m", "Qwen3.5-0.8B-Q4_K_M.gguf",
"-p", "Hello, my name is",
"-n", "128"
-n 控制单次生成的最大 token 数

# 问题三：llama_init_from_model函数做了什么功能？

# 问题四：为什么llama_model_load_from_file函数被调用三次？

1. 参数拟合探测：common_init_result 构造时先调用 llama_params_fit（common/common.cpp:1150），内部 llama_get_device_memory_data 会加载模型来估算内存（src/llama.cpp:81）。这次用 no_alloc=true、use_mmap=false，只读元数据/规划 buffer，不用于推理。
2.当需要减少上下文内存的情况发生，llama_params_fit_impl（src/llama.cpp）中329行代码也会调用llama_get_device_memory_data函数，进而调用到llama_model_load_from_file函数
3. 正式加载主模型：拟合结束后，同一构造函数执行真正的加载（common/common.cpp:1158），这份模型才用于推理。
