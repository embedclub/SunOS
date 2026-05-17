# llama.cpp 核心数据结构解析：`llama_model`

> 基于 `llama.cpp` 代码库 (commit: 114 种模型架构，GGUF v3)

---

## 目录

1. [整体结构概览](#1-整体结构概览)
2. [`llama_model` 成员详解](#2-llama_model-成员详解)
3. [`llama_hparams` — 模型超参数](#3-llama_hparams--模型超参数)
4. [`llama_vocab` — 词表与分词器](#4-llama_vocab--词表与分词器)
5. [`llama_layer` — 单层权重结构](#5-llama_layer--单层权重结构)
6. [注意力机制变体详解 (MHA / GQA / MQA / MLA)](#6-注意力机制变体详解-mha--gqa--mqa--mla)
7. [`llama_model::impl` — PImpl 隐藏实现](#7-llama_modelimpl--pimpl-隐藏实现)
8. [模型加载全流程](#8-模型加载全流程)
9. [GGUF 文件格式](#9-gguf-文件格式)
10. [设备管理与张量分配](#10-设备管理与张量分配)
11. [LoRA 适配器机制](#11-lora-适配器机制)

---

## 1. 整体结构概览

### 1.1 源码文件地图

```
include/
  llama.h               — C 风格公开 API 声明 (1589 行)
  llama-cpp.h           — C++ 封装

src/
  llama-model.h         — llama_model, llama_layer 等核心结构体定义 (640 行)
  llama-model.cpp       — 模型加载、图构建、查询方法 (9439 行)
  llama-model-loader.h  — llama_model_loader 声明 (207 行)
  llama-model-loader.cpp— GGUF 解析、张量加载、设备分配 (1695 行)
  llama-model-saver.h   — 模型保存接口
  llama-model-saver.cpp — 模型保存实现
  llama-hparams.h       — llama_hparams 超参数结构体 (356 行)
  llama-vocab.h         — llama_vocab 词表结构体 (188 行)
  llama-context.h/cpp   — llama_context 推理上下文
  llama-graph.h/cpp     — 计算图构建
  llama-arch.h/cpp      — 架构枚举与张量名称映射
  llama.cpp             — C API 实现 (入口调度层)
```

### 1.2 四层架构中的位置

```
┌──────────────────────────────────┐
│  tools/ (cli, server, quantize)  │  ← 应用层
├──────────────────────────────────┤
│  common/ (arg, log, sampling)    │  ← 工具层
├──────────────────────────────────┤
│  src/ (libllama)                 │  ← 推理引擎层  ←  llama_model 在此
│    ├── llama_model               │     模型表示
│    ├── llama_context             │     推理上下文
│    ├── llama_model_loader        │     模型加载器
│    └── models/*.cpp              │     各架构计算图
├──────────────────────────────────┤
│  ggml/ (libggml)                 │  ← 计算基座层
│    ├── ggml_tensor               │     张量
│    ├── ggml_cgraph               │     计算图
│    ├── ggml_backend              │     计算后端
│    └── ggml_cpu/ggml_cuda/...    │     各后端实现
└──────────────────────────────────┘
```

### 1.3 `llama_model` 整体结构图

```cpp
struct llama_model {
    // ── 身份标识 ──────────────────────────────
    llm_type type;          // 参数量级 (LLM_TYPE_7B, LLM_TYPE_70B, ...)
    llm_arch arch;          // 架构 (LLM_ARCH_LLAMA, LLM_ARCH_QWEN2, ...)
    std::string name;       // 模型名称

    // ── 核心数据 ──────────────────────────────
    llama_hparams hparams;  // 超参数 (层数、头数、维度等)
    llama_vocab   vocab;    // 词表与分词器数据

    // ── 顶层张量 (整个模型共享) ────────────────
    ggml_tensor * tok_embd;   // token 嵌入矩阵 [n_vocab, n_embd]
    ggml_tensor * type_embd;  // token type 嵌入 (可选)
    ggml_tensor * pos_embd;   // 位置嵌入 (绝对位置编码)
    ggml_tensor * tok_norm;   // 嵌入后 LayerNorm 权重
    ggml_tensor * tok_norm_b; // 嵌入后 LayerNorm bias

    // ── 输出层 ────────────────────────────────
    ggml_tensor * output_norm;      // 输出前 LayerNorm 权重
    ggml_tensor * output_norm_b;    // 输出前 LayerNorm bias
    ggml_tensor * output;           // lm_head [n_embd, n_vocab]
    ggml_tensor * output_b;         // lm_head bias
    ggml_tensor * output_norm_enc;  // encoder-decoder 的 encoder 输出 norm

    // ── 分类器 (embedding 模型) ───────────────
    ggml_tensor * cls / cls_b / cls_out / cls_out_b / cls_norm;
    ggml_tensor * conv1d / conv1d_b;

    // ── 特殊架构 (gemma3n altup) ──────────────
    ggml_tensor * altup_proj;
    ggml_tensor * altup_unembd_proj;
    ggml_tensor * per_layer_tok_embd;
    ggml_tensor * per_layer_model_proj;
    ggml_tensor * per_layer_proj_norm;

    // ── 逐层权重 ──────────────────────────────
    std::vector<llama_layer> layers;  // 每层的所有权重张量

    // ── SentenceTransformers 稠密层 ───────────
    ggml_tensor * dense_2_out_layers;
    ggml_tensor * dense_2_out_layers_b;
    ggml_tensor * dense_3_out_layers;

    // ── GGUF 元数据 ───────────────────────────
    std::unordered_map<std::string, std::string> gguf_kv;

    // ── 设备列表 ──────────────────────────────
    std::vector<llama_device> devices;

    // ── 调试/统计 ─────────────────────────────
    std::vector<std::pair<std::string, ggml_tensor *>> tensors_by_name;

    // ── LoRA 追踪 ─────────────────────────────
    std::unordered_set<llama_adapter_lora *> loras;

    // ── 内部实现 (PImpl) ──────────────────────
    llama_model_params params;
    std::unique_ptr<impl> pimpl;
};
```

---

## 2. `llama_model` 成员详解

### 2.1 身份标识

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | `llm_type` | 枚举表示模型参数量级，约 100 个值 |
| `arch` | `llm_arch` | 枚举表示模型架构，约 80+ 个值 |
| `name` | `std::string` | 从 GGUF `general.name` KV 读取 |

#### `llm_type` 枚举 (src/llama-model.h:22)

覆盖从 14M 到 744B 的模型规模。示例：

```cpp
LLM_TYPE_14M,    LLM_TYPE_70M,    LLM_TYPE_160M,
LLM_TYPE_0_5B,   LLM_TYPE_1B,     LLM_TYPE_3B,
LLM_TYPE_7B,     LLM_TYPE_8B,     LLM_TYPE_13B,
LLM_TYPE_30B,    LLM_TYPE_34B,    LLM_TYPE_65B,
LLM_TYPE_70B,    LLM_TYPE_236B,   LLM_TYPE_405B,
LLM_TYPE_671B,   LLM_TYPE_744B_A40B,

// MoE 特化
LLM_TYPE_8x7B,   LLM_TYPE_8x22B,   LLM_TYPE_16x12B,
LLM_TYPE_17B_16E,                   // Llama4 Scout
LLM_TYPE_17B_128E,                  // Llama4 Maverick

// 不确定规模的通用标记
LLM_TYPE_SMALL,  LLM_TYPE_MEDIUM,   LLM_TYPE_LARGE, LLM_TYPE_XL,
```

类型推断发生在 `load_hparams()` 中，每个架构的 switch-case 根据 `n_layer`、`n_embd`、`n_expert`、`n_head`、词表大小等组合来确定 `llm_type`。

#### `llm_arch` 枚举 (src/llama-arch.h:13)

覆盖 80+ 架构。示例：

```cpp
LLM_ARCH_LLAMA,      LLM_ARCH_LLAMA4,     LLM_ARCH_FALCON,
LLM_ARCH_GROK,       LLM_ARCH_BERT,       LLM_ARCH_MODERN_BERT,
LLM_ARCH_QWEN,       LLM_ARCH_QWEN2,      LLM_ARCH_QWEN2VL,
LLM_ARCH_QWEN3,      LLM_ARCH_QWEN3MOE,   LLM_ARCH_QWEN3VL,
LLM_ARCH_GEMMA,      LLM_ARCH_GEMMA2,     LLM_ARCH_GEMMA3,
LLM_ARCH_DEEPSEEK,   LLM_ARCH_DEEPSEEK2,  LLM_ARCH_DEEPSEEK3,
LLM_ARCH_MAMBA,      LLM_ARCH_RWKV6,      LLM_ARCH_RWKV7,
LLM_ARCH_PHI2,       LLM_ARCH_PHI3,       LLM_ARCH_PHIMOE,
LLM_ARCH_MINICPM,    LLM_ARCH_MINICPM3,   LLM_ARCH_EXAONE,
LLM_ARCH_NEMOTRON,   LLM_ARCH_GRANITE,    LLM_ARCH_GRANITE_MOE,
LLM_ARCH_CHAMELEON,  LLM_ARCH_COGVLM,     LLM_ARCH_T5,
// ... 等
```

### 2.2 `llama_model_params` — 模型加载参数 (include/llama.h:286)

用户在加载模型时通过此结构控制行为：

```cpp
struct llama_model_params {
    ggml_backend_dev_t * devices;                        // GPU 设备列表 (NULL = 全部)
    const struct llama_model_tensor_buft_override * tensor_buft_overrides; // 张量设备覆盖

    int32_t n_gpu_layers;                                // 卸载到 GPU 的层数
    enum llama_split_mode split_mode;                    // 多 GPU 拆分模式

    int32_t main_gpu;                                    // 主 GPU (split_mode == NONE 时)
    const float * tensor_split;                          // 各 GPU 负载比例

    llama_progress_callback progress_callback;            // 加载进度回调
    void * progress_callback_user_data;

    const struct llama_model_kv_override * kv_overrides;  // KV 元数据覆盖

    bool vocab_only;      // 仅加载词表
    bool use_mmap;        // 使用 mmap
    bool use_direct_io;   // 使用直接 I/O (覆盖 mmap)
    bool use_mlock;       // 锁定内存 (防止交换)
    bool check_tensors;   // 校验张量数据
    bool use_extra_bufts; // 使用额外 buffer 类型
    bool no_host;         // 不使用 host buffer
    bool no_alloc;        // 仅加载元数据，不分配数据
};
```

---

## 3. `llama_hparams` — 模型超参数

### 3.1 基础结构维度

| 字段 | 类型 | 说明 | 典型值 |
|------|------|------|--------|
| `n_ctx_train` | `uint32_t` | 训练时的上下文长度 | 8192, 131072 |
| `n_embd` | `uint32_t` | 隐藏层维度 (d_model) | 4096 (LLaMA-7B) |
| `n_embd_out_impl` | `uint32_t` | 输出嵌入维度 (0 = n_embd) | 0 |
| `n_layer` | `uint32_t` | Transformer 层数 | 32 (LLaMA-7B) |
| `n_layer_kv_from_start` | `int32_t` | 前 N 层有 KV cache (-1 = 全部) | -1 |

### 3.2 注意力头维度 (逐层可配)

| 字段 | 类型 | 说明 |
|------|------|------|
| `n_head_arr[il]` | `array<uint32_t, 512>` | 每层 query 头数 |
| `n_head_kv_arr[il]` | `array<uint32_t, 512>` | 每层 key/value 头数 (GQA) |
| `n_embd_head_k_full` | `uint32_t` | 全注意力的 key 头维度 (d_k) |
| `n_embd_head_v_full` | `uint32_t` | 全注意力的 value 头维度 (d_v) |
| `n_embd_head_k_swa` | `uint32_t` | SWA 层的 key 头维度 |
| `n_embd_head_v_swa` | `uint32_t` | SWA 层的 value 头维度 |
| `n_ff_arr[il]` | `array<uint32_t, 512>` | 每层 FFN 中间维度 |

> 特殊：当使用 `n_embd_head_k_mla_impl` / `n_embd_head_v_mla_impl` 时为 MLA (DeepSeek2) 的内部头大小。

快捷方法：

```cpp
uint32_t n_head(uint32_t il = 0) const;     // il 层的 query 头数
uint32_t n_head_kv(uint32_t il = 0) const;  // il 层的 k/v 头数
uint32_t n_ff(uint32_t il = 0) const;       // il 层的 FFN 维度
uint32_t n_gqa(uint32_t il = 0) const;      // GQA 分组数 = n_head / n_head_kv
uint32_t n_rot(uint32_t il = 0) const;      // RoPE 维度
```

### 3.3 MoE (混合专家)

| 字段 | 类型 | 说明 |
|------|------|------|
| `n_expert` | `uint32_t` | 专家总数 (0 = 非 MoE) |
| `n_expert_used` | `uint32_t` | 每 token 激活的专家数 |
| `n_expert_shared` | `uint32_t` | 共享专家数 |
| `n_ff_exp` | `uint32_t` | 每个专家的 FFN 维度 |
| `n_ff_shexp` | `uint32_t` | 共享专家的 FFN 维度 |
| `n_ff_chexp` | `uint32_t` | 分组专家 (adjugate) 的 FFN 维度 |
| `n_expert_groups` | `uint32_t` | 专家组数 (DeepSeekV3 路由) |
| `n_group_used` | `uint32_t` | 每组选中的 token 数 |
| `n_group_experts` | `uint32_t` | 每组专家数 |
| `expert_gating_func` | `uint32_t` | 门控函数类型 |
| `moe_every_n_layers` | `uint32_t` | 每隔 N 层使用 MoE |
| `n_layer_dense_lead` | `uint32_t` | 开头多少层为 dense (非 MoE) |

门控函数类型枚举：

```cpp
enum llama_expert_gating_func_type {
    LLAMA_EXPERT_GATING_FUNC_TYPE_NONE           = 0,
    LLAMA_EXPERT_GATING_FUNC_TYPE_SOFTMAX        = 1,  // 标准 softmax
    LLAMA_EXPERT_GATING_FUNC_TYPE_SIGMOID        = 2,  // sigmoid (DeepSeekV3)
    LLAMA_EXPERT_GATING_FUNC_TYPE_SOFTMAX_WEIGHT = 3,  // 应用到路由权重
};
```

### 3.4 Normalization

| 字段 | 说明 |
|------|------|
| `f_norm_eps` | LayerNorm epsilon |
| `f_norm_rms_eps` | RMSNorm epsilon (大多数模型) |
| `f_norm_group_eps` | GroupNorm epsilon |

### 3.5 RoPE (旋转位置编码)

| 字段 | 说明 |
|------|------|
| `rope_freq_base_train` | 训练时的 RoPE 频率基数 |
| `rope_freq_base_train_swa` | SWA 层的 RoPE 基数 |
| `rope_freq_scale_train` | 训练时的频率缩放 |
| `rope_freq_scale_train_swa` | SWA 层的缩放 |
| `rope_scaling_type_train` | 缩放类型 (linear / yarn / ...) |
| `rope_attn_factor` | 注意力缩放因子 |
| `rope_finetuned` | RoPE 是否经过微调 |
| `n_ctx_orig_yarn` | YaRN 原始上下文长度 |
| `rope_yarn_log_mul` | YaRN 对数乘数 |
| `rope_sections[4]` | 部分 RoPE 维度分段 (Qwen2 等) |

### 3.6 滑动窗口注意力 (SWA)

| 字段 | 说明 |
|------|------|
| `swa_type` | SWA 类型 (None / Standard / Chunked / Symmetric) |
| `n_swa` | 滑动窗口大小 |
| `swa_layers[il]` | 逐层标记该层是否为 SWA |

SWA 模式控制方法：

```cpp
void set_swa_pattern(uint32_t n_pattern, bool dense_first = false);
// n_pattern=4, dense_first=false: 3 层 SWA, 1 层全注意力, 循环
```

### 3.7 状态空间模型 (SSM)

用于 Mamba、RWKV 等非 Transformer 架构：

| 字段 | 说明 |
|------|------|
| `ssm_d_conv` | 卷积核大小 |
| `ssm_d_inner` | SSM 内部维度 |
| `ssm_d_state` | SSM 状态维度 |
| `ssm_dt_rank` | 时间步长 rank |
| `ssm_n_group` | 组数 (Mamba-2) |

### 3.8 混合模型

| 字段 | 说明 |
|------|------|
| `recurrent_layer_arr[il]` | 标记哪些层为循环层 (SSM) |
| `ssm_dt_b_c_rms` | 对 SSM dt_B 应用 RMSNorm |

### 3.9 注意力配置

| 字段 | 说明 |
|------|------|
| `causal_attn` | 因果注意力 vs 双向 |
| `use_alibi` | 使用 ALiBi 位置偏置 |
| `attn_soft_cap` | 注意力 logit soft-capping |
| `use_kq_norm` | 在 RoPE 后对 K/Q 做 norm |
| `f_clamp_kqv` | K/Q/V 值裁剪 |
| `f_max_alibi_bias` | ALiBi 最大偏置 |
| `f_logit_scale` | logit 缩放 |
| `f_attn_logit_softcapping` | 注意力 logit soft-cap 阈值 |
| `f_router_logit_softcapping` | 路由 logit soft-cap 阈值 |
| `f_final_logit_softcapping` | 最终 logit soft-cap 阈值 |

### 3.10 特殊架构字段

| 字段 | 所属架构 | 说明 |
|------|----------|------|
| `n_embd_head_kda` | Kimi K2 | KDA 头维度 |
| `n_altup / i_altup_act / n_embd_altup` | Gemma3n | AltUp 参数 |
| `laurel_rank` | Gemma3n | Laurel 低秩维度 |
| `dense_2_feat_in/out, dense_3_feat_in/out` | Sentence Transformers | 稠密层维度 |
| `indexer_n_head / head_size / top_k` | DeepSeek | DSA (稀疏注意力) 索引器 |
| `n_deepstack_layers` | Qwen3VL | DeepStack 层数 |
| `n_embd_per_layer` | Gemma4 | 每层嵌入维度 |
| `dec_start_token_id, dec_n_layer` | T5/FLAN-T5 | Encoder-Decoder 解码器参数 |

### 3.11 GGUF 元数据加载流程

`llama_hparams` 从 GGUF KV (key-value) 对读取。`llama_model_loader::get_key<T>()` 模板函数：

```cpp
// src/llama-model-loader.cpp:398
template<typename T>
static bool get_key(const gguf_context * ctx, const char * key, T & target,
                    const struct llama_model_kv_override * ovrd = nullptr) {
    const int kid = gguf_find_key(ctx, key);
    if (kid == -1) return false;  // 不存在的 key 返回 false
    // 检查是否有 override
    if (ovrd && ovrd->tag == /* 匹配类型 */) {
        target = ovrd->val_...;
        return true;
    }
    // 从 GGUF 读取
    target = gguf_get_val_...(ctx, kid);
    return true;
}
```

对逐层参数 (如 `n_head_arr`)，使用 `get_key_or_arr()`：

```cpp
// src/llama-model-loader.cpp:437
// 支持两种 GGUF 存储方式：
// 1. 标量: 所有层共享同一个值
// 2. 数组: 每层独立值
template<typename T, size_t N>
static void get_key_or_arr(const gguf_context * ctx, const char * key,
                           std::array<T, N> & target, uint32_t n_layer,
                           const struct llama_model_kv_override * ovrd = nullptr)
```

---

## 4. `llama_vocab` — 词表与分词器

### 4.1 结构定义 (src/llama-vocab.h:67)

```cpp
struct llama_vocab {
    struct token_data {
        std::string text;          // token 文本
        float score;               // 分数/概率
        llama_token_attr attr;     // token 属性
    };

    // 加载方法
    void load(llama_model_loader & ml, const LLM_KV & kv);

    // 类型查询
    enum llama_vocab_type     get_type()     const;  // SPM / BPE / WPM / UGM / RWKV
    enum llama_vocab_pre_type get_pre_type() const;  // 预分词器类型 (50 种)
    uint32_t n_tokens()    const;                    // 词表大小
    uint32_t n_token_types() const;

    // 属性检查
    bool is_normal(id) const;       // 普通 token
    bool is_unknown(id) const;      // <unk>
    bool is_control(id) const;      // 控制 token
    bool is_byte(id) const;         // byte token
    bool is_user_defined(id) const;
    bool is_unused(id) const;
    bool is_eog(id) const;          // end-of-generation token

    uint8_t     token_to_byte(id) const;   // byte token → byte value
    llama_token byte_to_token(ch)  const;  // byte → token ID
};
```

### 4.2 分词器类型

```cpp
enum llama_vocab_type {
    LLAMA_VOCAB_TYPE_SPM  = 0,   // SentencePiece (Unigram)
    LLAMA_VOCAB_TYPE_BPE  = 1,   // Byte-Pair Encoding (GPT-2)
    LLAMA_VOCAB_TYPE_WPM  = 2,   // WordPiece (BERT)
    LLAMA_VOCAB_TYPE_UGM  = 3,   // Unigram (T5)
    LLAMA_VOCAB_TYPE_RWKV = 4,   // RWKV tokenizer
};
```

### 4.3 预分词器类型 (50 种)

决定在 tokenize 之前如何对原始文本做预处理。示例：

```cpp
LLAMA_VOCAB_PRE_TYPE_DEFAULT,         // 通用
LLAMA_VOCAB_PRE_TYPE_LLAMA3,          // LLaMA 3 专用
LLAMA_VOCAB_PRE_TYPE_DEEPSEEK_LLM,    // DeepSeek LLM
LLAMA_VOCAB_PRE_TYPE_DEEPSEEK_CODER,  // DeepSeek Coder
LLAMA_VOCAB_PRE_TYPE_FALCON,          // Falcon
LLAMA_VOCAB_PRE_TYPE_GPT2,            // GPT-2
LLAMA_VOCAB_PRE_TYPE_QWEN2,           // Qwen2
LLAMA_VOCAB_PRE_TYPE_CHATGLM4,        // ChatGLM-4
LLAMA_VOCAB_PRE_TYPE_GEMMA4,          // Gemma-4
// ... 共 50 种
```

---

## 5. `llama_layer` — 单层权重结构

### 5.1 总体设计

`llama_layer` 是一个**包含所有可能权重指针**的大结构体，约 150+ 个 `ggml_tensor*` 成员。未使用的保持 `nullptr`。这使得代码可以统一处理所有架构，但内存上略有浪费。

### 5.2 按功能分类

```cpp
struct llama_layer {
    // ── 归一化层 ────────────────────────────────────
    ggml_tensor * attn_norm;          // 注意力前 norm    权重
    ggml_tensor * attn_norm_b;        //                   bias
    ggml_tensor * attn_norm_2;        // 第二注意力 norm (并行注意力)
    ggml_tensor * attn_q_norm;        // Q 的 norm (use_kq_norm)
    ggml_tensor * attn_k_norm;        // K 的 norm
    ggml_tensor * attn_out_norm;      // 注意力输出 norm
    ggml_tensor * ffn_norm;           // FFN 前 norm
    ggml_tensor * ffn_norm_b;         //           bias
    ggml_tensor * ffn_post_norm;      // 残差后 post-norm

    // ── 注意力投影 ──────────────────────────────────
    ggml_tensor * wq;                 // Q 权重     [n_embd, n_head * d_head]
    ggml_tensor * wk;                 // K 权重     [n_embd, n_head_kv * d_head]
    ggml_tensor * wv;                 // V 权重     [n_embd, n_head_kv * d_head]
    ggml_tensor * wo;                 // 输出投影   [n_head * d_head, n_embd]
    ggml_tensor * wqkv;              // 融合 QKV   [n_embd, (n_head+2*n_head_kv) * d_head]
    ggml_tensor * wq_a, * wq_b;      // MLA: Q 低秩分解 A/B
    ggml_tensor * wkv_a_mqa;         // MLA: KV 压缩
    ggml_tensor * wkv_b;             // MLA: KV 解压缩
    ggml_tensor * wk_b, * wv_b;      // MLA: 吸收模式 K nope / V 解压缩

    // ── FFN (稠密) ──────────────────────────────────
    ggml_tensor * ffn_gate;          // 门控     [n_embd, n_ff]
    ggml_tensor * ffn_down;          // 下投影   [n_ff, n_embd]
    ggml_tensor * ffn_up;            // 上投影   [n_embd, n_ff]

    // ── FFN (MoE) ───────────────────────────────────
    ggml_tensor * ffn_gate_inp;      // 路由     [n_embd, n_expert]
    ggml_tensor * ffn_gate_exps;     // 专家门控 [n_ff_exp, n_expert, n_embd]
    ggml_tensor * ffn_down_exps;     // 专家下投 [n_ff_exp, n_embd, n_expert]
    ggml_tensor * ffn_up_exps;       // 专家上投 [n_embd, n_ff_exp, n_expert]
    ggml_tensor * ffn_gate_up_exps;  // 融合门控+上投 [n_ff_exp*2, n_embd, n_expert]

    // ── 共享专家 ────────────────────────────────────
    ggml_tensor * ffn_gate_shexp;
    ggml_tensor * ffn_down_shexp;
    ggml_tensor * ffn_up_shexp;

    // ── SSM (Mamba) ─────────────────────────────────
    ggml_tensor * ssm_in;            // 输入投影
    ggml_tensor * ssm_x;             // x 投影
    ggml_tensor * ssm_dt;            // 时间步长投影
    ggml_tensor * ssm_out;           // 输出投影
    ggml_tensor * ssm_conv1d;        // 1D 卷积
    ggml_tensor * ssm_a;             // 状态矩阵 A
    ggml_tensor * ssm_d;             // 跳跃连接 D

    // ── RWKV 时间混合 ───────────────────────────────
    ggml_tensor * time_mix_w1, * time_mix_w2;
    ggml_tensor * time_mix_lerp_x, * time_mix_lerp_k, ...;
    ggml_tensor * time_mix_key, * time_mix_value;
    ggml_tensor * time_mix_receptance, * time_mix_gate;
    ggml_tensor * time_mix_decay;
    // ... RWKV7 额外字段

    // ── BitNet 低比特缩放 ───────────────────────────
    ggml_tensor * wq_s, * wk_s, * wv_s, * wo_s;   // 权重缩放
    ggml_tensor * ffn_gate_s, * ffn_up_s, * ffn_down_s;
    ggml_tensor * wq_in_s, * wk_in_s, ...;          // 输入缩放

    // ── RoPE ────────────────────────────────────────
    ggml_tensor * rope_long, * rope_short, * rope_freqs;

    // ── 相对位置偏置 ────────────────────────────────
    ggml_tensor * attn_rel_b;
    ggml_tensor * attn_rel_b_enc;
    ggml_tensor * attn_rel_b_cross;

    // ── Encoder-Decoder ────────────────────────────
    ggml_tensor * wq_cross, * wk_cross, * wv_cross, * wo_cross;
    ggml_tensor * wq_enc, * wk_enc, * wv_enc, * wo_enc;

    // ── DSA (DeepSeek 稀疏注意力) ───────────────────
    ggml_tensor * indexer_k_norm, * indexer_proj, * indexer_attn_k;

    // ── 子结构 ──────────────────────────────────────
    llama_layer_posnet    posnet;     // WaveTokenizer 位置网络
    llama_layer_convnext convnext;    // ConvNeXt 块
    llama_layer_shortconv shortconv;  // 短卷积
    llama_layer_nextn     nextn;     // 下一个 token 预测层
};
```

### 5.3 张量命名规范

通过 `llama-arch.cpp` 的张量名称映射表，将标准化的张量名映射为确定架构的具体名称。

标准名格式：`blk.{layer_id}.{tensor_type}.{weight_type}`

示例：
```
blk.0.attn_q.weight    →  layers[0].wq
blk.0.attn_k.weight    →  layers[0].wk
blk.0.attn_output.weight → layers[0].wo
blk.0.ffn_gate.weight  →  layers[0].ffn_gate
blk.0.ffn_down.weight  →  layers[0].ffn_down
blk.0.ffn_up.weight    →  layers[0].ffn_up
```

每个架构在 `llama-arch.cpp` 中定义自己的 `llm_tensor_info` 数组（约 100-200 个条目）实现具体名称的映射。

---

## 6. 注意力机制变体详解 (MHA / GQA / MQA / MLA)

### 6.1 MHA (Multi-Head Attention) — 标准多头注意力

```
条件: n_head == n_head_kv       (每对 Q 都对应独立的 K/V)
张量: wq [n_embd, n_head*d]    wk [n_embd, n_head*d]   wv [n_embd, n_head*d]
       wo [n_head*d, n_embd]
```

每个注意力头有独立的 query、key、value 投影。

### 6.2 GQA (Grouped Query Attention) — 分组查询注意力

```
条件: n_head > n_head_kv, n_head % n_head_kv == 0
      每组 n_gqa = n_head / n_head_kv 个 Q 共享一组 K/V
张量: wq [n_embd, n_head*d]    wk [n_embd, n_head_kv*d]
       wv [n_embd, n_head_kv*d]    wo [n_head*d, n_embd]
```

LLaMA 2/3、Mistral 等广泛使用。例如 LLaMA-3-8B: `n_head=32, n_head_kv=8, n_gqa=4`。

### 6.3 MQA (Multi-Query Attention) — 多查询注意力

```
条件: n_head_kv == 1, n_head 任意
      所有 Q 共享同一组 K/V
张量: wk [n_embd, d]    wv [n_embd, d]
```

Falcon、PaLM 等使用。GQA 的特例 (`n_gqa = n_head`)。

### 6.4 MLA (Multi-head Latent Attention) — DeepSeek2 多头潜在注意力

MLA 通过低秩压缩大幅减少 KV cache 大小。两种模式：

#### 模式 A：吸收优化 (默认, `lite=false`)

```
推理流程:
1. Q 压缩:  q = wq_b(norm(wq_a(x)))          ← 低秩分解
2. Q 拆分:  q_nope [d-d_rope] + q_pe [d_rope]
3. KV 压缩: kv_cmpr_pe = wkv_a_mqa(x)        ← 压缩到 kv_lora_rank + d_rope
            kv_cmpr    = kv_cmpr_pe[:kv_lora_rank]
            k_pe       = kv_cmpr_pe[kv_lora_rank:]
4. 吸收:    wk_b 被吸收到 q_nope 的投影中
            q_nope_absorbed = wk_b(q_nope)
            Qcur = concat(q_nope_absorbed, q_pe)
            Kcur = concat(kv_cmpr, k_pe)       ← 只用压缩后的 KV
            Vcur = kv_cmpr                      ← 不用单独 V！
5. 注意力:  在 MHA 计算后，用 wv_b 解压缩 V
```

效果：KV cache 从 `2 * n_head_kv * d * n_layer` 变为 `(kv_lora_rank + d_rope) * n_layer`

#### 模式 B：无吸收 (`lite=true`)

```cpp
// src/models/deepseek2.cpp:187-224
kv = wkv_b(kv_cmpr_pe)  // 完全解压缩到 MHA
k_nope = kv[:n_embd_head_qk_nope]
Vcur   = kv[n_embd_head_qk_nope:]
Kcur   = concat(k_nope, k_pe)
// 之后作为标准 MHA 计算
```

#### 张量对应关系：

```
wq_a: [n_embd, n_head * (d - d_rope)]            // Q 压缩 (nope 部分)
wq_b: [n_head * (d - d_rope), n_head * d]        // Q 解压缩
wkv_a_mqa: [n_embd, kv_lora_rank + d_rope]       // KV 压缩
wk_b:  [n_head * (d - d_rope), n_head * d]       // K 吸收 (nope)
wv_b:  [kv_lora_rank, n_head * d_v]              // V 解压缩 (attn 时使用)
```

### 6.5 融合 QKV

一些模型 (Falcon, Phi-3) 将 Q、K、V 的三个投影合并为一个张量：

```cpp
// src/llama-graph.cpp:1076-1095
if (layer.wqkv) {
    qkv = ggml_mul_mat(layer.wqkv, cur);
    // 将一个矩阵视图分割为 Q、K、V 三个部分
    Qcur = ggml_view_3d(qkv, ..., 0);                        // 第一部分
    Kcur = ggml_view_3d(qkv, ..., offset_Q);                  // 中间部分
    Vcur = ggml_view_3d(qkv, ..., offset_Q + offset_K);       // 最后部分
}
```

### 6.6 计算图构建：`build_attn_mha()` (src/llama-graph.cpp:1932)

```
1. reshape Q/K/V 为 [d_head, n_tokens, n_head, n_stream]
2. 选择路径:
   ├── Flash Attention:
   │     kqv = ggml_flash_attn_ext(Q, K, V, mask, scale)
   │     (可选: v_mla 解压缩)
   └── 标准 MHA:
         kq = K @ Q^T                         [n_tokens, n_tokens, n_head, n_stream]
         kq = softmax(kq / sqrt(d) + mask)
         kqv = V @ softmax(KQ)                [d_head, n_tokens, n_head, n_stream]
3. 重排并 reshape 回 [n_tokens, n_head * d_head]
4. wo 投影
```

---

## 7. `llama_model::impl` — PImpl 隐藏实现

### 7.1 定义 (src/llama-model.cpp:633)

```cpp
struct llama_model::impl {
    // ── 统计 ──────────────────────────────────
    uint64_t n_elements;        // 总参数量
    size_t   n_bytes;           // 总字节数 (含量化)
    std::string desc_str;       // 描述字符串 ("LLaMA v3 8B Q4_K_M 等)

    // ── 文件映射 ──────────────────────────────
    llama_mmaps mappings;       // mmap 对象列表 (支持多文件分片)
    llama_mlocks mlock_bufs;    // 锁定在内存中的缓冲区
    llama_mlocks mlock_mmaps;   // 锁定在内存中的 mmap

    // ── 后端缓冲区 ────────────────────────────
    std::vector<std::pair<ggml_context_ptr,
        std::vector<ggml_backend_buffer_ptr>>> ctxs_bufs;
        // 每个 ggml_context + 其所有 backend buffer
        // 一个 buft (buffer type) 对应一个 context
        // 一个 context 可能持有多个 buffer (主 buffer + 额外 buft)

    // ── Buffer 类型列表 ───────────────────────
    buft_list_t cpu_buft_list;
    std::map<ggml_backend_dev_t, buft_list_t> gpu_buft_list;

    // ── 逐层设备分配 ──────────────────────────
    struct layer_dev {
        ggml_backend_dev_t dev;      // 设备 (CPU / CUDA0 / Metal)
        buft_list_t * buft_list;     // 该设备支持的 buffer 类型
    };
    layer_dev dev_input;              // 输入层设备 (tok_embd)
    layer_dev dev_output;             // 输出层设备 (lm_head)
    std::vector<layer_dev> dev_layer; // 每层的设备分配

    // ── 张量类型覆盖 ──────────────────────────
    bool has_tensor_overrides;
};
```

### 7.2 `llama_mmap` 详解 (src/llama-mmap.h/cpp)

#### POSIX 实现

```cpp
// src/llama-mmap.cpp:437
impl(struct llama_file * file, size_t prefetch, bool numa) {
    size = file->size();
    fd = file->file_id();
    flags = MAP_SHARED;

    addr = mmap(NULL, file->size(), PROT_READ, flags, fd, 0);
    // MAP_SHARED: 与其他进程共享映射
    // PROT_READ: 只读映射

    // Linux 预取优化
    posix_fadvise(fd, 0, 0, POSIX_FADV_SEQUENTIAL);
    // 预期顺序访问 → 内核提前读

    if (prefetch > 0) {
        flags |= MAP_POPULATE;    // 立刻加载页面到内存
        posix_madvise(addr, prefetch, POSIX_MADV_WILLNEED);
        // 通知内核即将访问这些页面
    }

    if (numa) {
        posix_madvise(addr, size, POSIX_MADV_RANDOM);
        // NUMA 系统上避免迁移开销
    }
}
```

#### `unmap_fragment()` — 选择性释放

```cpp
// src/llama-mmap.cpp:482
void unmap_fragment(size_t first, size_t last) {
    // 只释放文件头部元数据 和/或 尾部未使用的区域
    // 保留中间张量数据占据的页面
    // 使用 MADV_DONTNEED 释放物理页面 (Linux)
    // 使用 VirtualUnmap (Windows)
}
```

调用时机：`load_all_data()` 全部加载后，释放 GGUF 头部和尾部未使用空间。

### 7.3 `llama_mlock` — 内存锁定

```cpp
// src/llama-mmap.cpp:628
// 用途: 防止操作系统将模型数据交换到磁盘

void grow_to(size_t target_size) {
    while (current_size < target_size) {
        size_t chunk = std::min(granularity, target_size - current_size);
        // POSIX: mlock(addr + current_size, chunk)
        // Windows: VirtualLock(addr + current_size, chunk)
        current_size += chunk;
    }
}
```

---

## 8. 模型加载全流程

### 8.1 入口函数调用链

```
llama_load_model_from_file(file, params)        ← include/llama.h
  └─ llama_model_load_from_file_impl(file, params)  ← src/llama-model.cpp:931
       └─ llama_model_loader(file, params)         ← src/llama-model-loader.cpp:510
            ├─ gguf_init_from_file()               ← 解析 GGUF 头部
            ├─ 创建 ggml_context (仅元数据)
            ├─ 扫描所有张量的名称、形状、偏移
            ├─ 如果多文件分片，依次打开
            └─ 确定文件量化类型

       └─ model = new llama_model(params)          ← 创建空模型壳

       └─ model->load_arch(ml)                     ← 读取架构
       └─ model->load_hparams(ml)                  ← 读取超参数
       └─ model->load_vocab(ml)                    ← 读取词表
       └─ model->load_tensors(ml)                  ← 加载张量 (最关键)
            └─ ml.create_tensor()                  ← 为每个张量分配后端缓冲区
            └─ ml.load_all_data()                  ← 填充张量数据

       └─ model->print_info()                      ← 打印模型信息
```

### 8.2 `load_tensors()` 详解

这是最复杂的过程，包含设备分配和缓冲区管理。

#### 步骤 1: `create_tensor()` — 确定 buffer 类型

```cpp
// src/llama-model-loader.cpp:1045
// 为每个 tensor 选择最优的 buffer type (CPU / CUDA / Metal 等)

// Step 1: 为每个 buffer type 创建 ggml_context
auto ctx_for_buft = [&](ggml_backend_buffer_type_t buft) -> ggml_context* {
    if (ctx_map.count(buft)) return ctx_map[buft];
    ctx = ggml_init({n_mem, NULL, no_alloc});  // no_alloc: 只记录元数据
    ctx_map[buft] = ctx;
    return ctx;
};

// Step 2: 为 tensor 选择 buffer type
auto buft_for_tensor = [&](const llama_tensor_info & info) -> ggml_backend_buffer_type_t {
    auto op = info.op;  // GGML_OP_MUL_MAT (权重) / GGML_OP_ADD (bias) 等
    auto tensor_layer = info.layer;  // INPUT / OUTPUT / REPEATING

    // 遍历设备列表，找到第一个支持该操作 + 该数据类型的 buft
    for (auto & [dev, buft_list] : get_buft_list(tensor_layer)) {
        for (auto & buft : buft_list) {
            if (weight_buft_supported(buft, dev, cur, op)) return buft;
        }
    }
};

// Step 3: 在选定的 context 中创建 ggml_tensor 元数据
ggml_tensor * cur = ggml_dup_tensor(ctx, cur_ggml_tensor);
```

#### 步骤 2: `load_all_data()` — 加载实际数据

```cpp
// src/llama-model-loader.cpp:1399
void load_all_data(bool use_mpu, progress_callback) {
    // 设置异步上传机制 (GPU offloading)
    // 创建 4 个 64MB 的 staging buffer
    // 启动异步读取线程

    for (每个 tensor) {
        auto * cur = tensor;
        const void * data = mmap_addr + weight->offs;

        if (use_mmap && buf_mmap && cur->data == nullptr) {
            // 零拷贝路径: 直接将 mmap 地址作为 tensor 的数据指针
            ggml_backend_tensor_alloc(buf_mmap, cur, data);
            // 适用于 CPU 或 host-accessible buffer
        } else if (use_mmap) {
            // 从 mmap 拷贝到设备 (GPU)
            ggml_backend_tensor_set(cur, data, 0, n_size);
        } else {
            // 从文件读取
            file->read_raw(staging_buf, n_size);
            ggml_backend_tensor_set(cur, staging_buf, 0, n_size);
            // 或异步: async_read + async_upload
        }
    }

    // 加载完成后，释放未使用的 mmap 页面
    if (use_mmap) {
        for (auto & mapping : mappings) {
            mapping->unmap_fragment(0, mmap_used_first);       // 释放头部
            mapping->unmap_fragment(mmap_used_last, size);     // 释放尾部
        }
    }
}
```

### 8.3 多文件分片 (Split)

GGUF 模型可以拆分为多个文件（如 `model-00001-of-00005.gguf`）。`llama_model_loader` 处理方式：

```cpp
// src/llama-model-loader.cpp:588
// 读取第一个文件后，通过 general.alignment 等元数据确定分片数
// 依次打开后续文件，合并到同一 weights_map 中
for (int i = 1; i < n_split; i++) {
    auto fname_split = build_split_fname(fname_base, i, n_split);
    files.emplace_back(std::make_unique<llama_file>(fname_split));
    // 读取该分片的张量信息，合并到 weights_map
}
```

---

## 9. GGUF 文件格式

### 9.1 文件布局 (ggml/include/gguf.h:1)

```
┌────────────────────────────────────────┐
│ Magic: "GGUF" (4 bytes)                │
├────────────────────────────────────────┤
│ Version (uint32_t, 当前 = 3)           │
├────────────────────────────────────────┤
│ n_tensors (int64_t)                    │
├────────────────────────────────────────┤
│ n_kv (int64_t)                         │
├────────────────────────────────────────┤
│ KV 键值对列表                           │
│  每个: key (string)                    │
│       + type (gguf_type)               │
│       + value (根据 type 编码)         │
│  若 type == ARRAY:                     │
│       + element_type (gguf_type)       │
│       + n_elements (int64_t)           │
│       + elements 数据                  │
├────────────────────────────────────────┤
│ Tensor 元数据列表                       │
│  每个: name (string)                   │
│       + n_dims (uint32_t)              │
│       + dim[0..n_dims-1] (int64_t[])  │
│       + type (ggml_type)               │
│       + offset (uint64_t)              │
├────────────────────────────────────────┤
│ 对齐填充 (到 alignment=32 bytes)        │
├────────────────────────────────────────┤
│ Tensor 数据块                          │
│  按 tensor 定义中的 offset 寻址        │
└────────────────────────────────────────┘
```

### 9.2 值类型

```cpp
enum gguf_type {
    GGUF_TYPE_UINT8   = 0,
    GGUF_TYPE_INT8    = 1,
    GGUF_TYPE_UINT16  = 2,
    GGUF_TYPE_INT16   = 3,
    GGUF_TYPE_UINT32  = 4,
    GGUF_TYPE_INT32   = 5,
    GGUF_TYPE_FLOAT32 = 6,
    GGUF_TYPE_BOOL    = 7,     // 存储为 int8_t
    GGUF_TYPE_STRING  = 8,     // uint64_t 长度 + UTF-8 数据
    GGUF_TYPE_ARRAY   = 9,     // 元素类型 + 计数 + 数据
    GGUF_TYPE_UINT64  = 10,
    GGUF_TYPE_INT64   = 11,
    GGUF_TYPE_FLOAT64 = 12,
};
```

### 9.3 关键 GGUF KV 键

| 键 | 类型 | 说明 |
|----|------|------|
| `general.architecture` | string | 架构名 (如 "llama") |
| `general.name` | string | 模型名称 |
| `general.alignment` | uint32 | 数据对齐 (默认 32) |
| `llama.context_length` | uint32 | 训练上下文长度 |
| `llama.embedding_length` | uint32 | 嵌入维度 (n_embd) |
| `llama.block_count` | uint32 | 层数 |
| `llama.attention.head_count` | uint32 | 注意力头数 |
| `llama.attention.head_count_kv` | uint32 | K/V 头数 |
| `llama.feed_forward_length` | uint32 | FFN 维度 |
| `llama.expert_count` | uint32 | MoE 专家数 |
| `llama.expert_used_count` | uint32 | 激活专家数 |
| `llama.rope.freq_base` | float32 | RoPE 基数 |
| `llama.rope.scaling.type` | string | 缩放类型 |
| `general.file_type` | int32 | 量化类型枚举 |
| `tokenizer.ggml.model` | string | 分词器模型类型 |
| `tokenizer.ggml.tokens` | array[string] | 词表 |

### 9.4 GGUF API 函数

```cpp
gguf_context * gguf_init_from_file(const char * fname, struct gguf_init_params params);
// params: { .no_alloc = true, .ctx = &ggml_ctx }

// 元数据
int     gguf_get_n_kv(gguf_context*);           // KV 对数
int     gguf_find_key(gguf_context*, const char*); // 按名查找索引
gguf_type gguf_get_kv_type(gguf_context*, int); // 值类型
const char * gguf_get_key(gguf_context*, int);  // 按索引获取键名

// 张量信息
int      gguf_get_n_tensors(gguf_context*);
uint64_t gguf_get_tensor_offset(gguf_context*, int);
const char * gguf_get_tensor_name(gguf_context*, int);
enum ggml_type gguf_get_tensor_type(gguf_context*, int);

// 写入
void gguf_write_to_file(gguf_context*, const char*, bool only_meta);
```

---

## 10. 设备管理与张量分配

### 10.1 `llama_device` 结构

```cpp
struct llama_device {
    bool is_meta;                  // 是否是 "meta" 设备 (虚拟设备)
    ggml_backend_dev_t dev;        // ggml 后端设备句柄
};
```

`is_meta` 用于 `LLAMA_SPLIT_MODE_TENSOR` 模式，在这种模式下张量不会被实际分配，只是为了获取拆分信息。

### 10.2 拆分模式 (`llama_split_mode`)

| 模式 | 说明 |
|------|------|
| `LLAMA_SPLIT_MODE_NONE` | 所有层都在 `main_gpu` |
| `LLAMA_SPLIT_MODE_LAYER` | 按层拆分：将连续的层组分配到不同 GPU |
| `LLAMA_SPLIT_MODE_ROW` | 按行拆分：FFN 矩阵按行切分到不同 GPU |
| `LLAMA_SPLIT_MODE_TENSOR` | 按张量拆分：单个张量跨 GPU 切分 |

### 10.3 逐层设备选择

```cpp
// src/llama-model.h:609
ggml_backend_dev_t llama_model::dev_layer(int il) const {
    return pimpl->dev_layer[il].dev;
}
```

在 `create_tensor()` 期间，`select_weight_buft()` 使用以下策略：

```
1. 如果 tensor_buft_overrides 匹配该张量名模式 → 使用指定的 buft
2. 否则:
   a. INPUT 层 (tok_embd) → dev_input.buft_list
   b. OUTPUT 层 (lm_head) → dev_output.buft_list
   c. 其他重复层 (layer 权重) → dev_layer[il % n_devices].buft_list
3. 对列表中的每个 buft，测试 weight_buft_supported()
   - 创建同形状、同类型的临时张量
   - ggml_backend_dev_supports_op(dev, temp_tensor, op)
   - 如果支持，选择该 buft；否则尝试下一个
```

### 10.4 `weight_buft_supported()` 测试

```cpp
// src/llama-model-loader.cpp:893
bool weight_buft_supported(ggml_backend_buffer_type_t buft,
                          ggml_backend_dev_t dev,
                          const ggml_tensor * cur, ggml_op op) {
    // 创建临时同形张量
    ggml_init_params params = { /* ... */ };
    ggml_context * ctx = ggml_init(params);
    ggml_tensor * tensor = ggml_dup_tensor(ctx, cur);

    // 分配测试缓冲区
    ggml_backend_buffer_t buf = ggml_backend_buft_alloc_buffer(buft, ...);
    ggml_backend_tensor_alloc(buf, tensor, ...);

    // 测试操作是否支持
    bool supported = ggml_backend_dev_supports_op(dev, tensor, op);

    ggml_free(ctx);
    return supported;
}
```

---

## 11. LoRA 适配器机制

### 11.1 追踪

```cpp
// llama_model 中的 loras 集合
std::unordered_set<llama_adapter_lora *> loras;

~llama_model() {
    for (auto * lora : loras) {
        delete lora;  // 模型析构时自动清理所有关联 LoRA
    }
}
```

### 11.2 使用流程

```cpp
// API 调用顺序
llama_adapter_lora_init(model, lora_file);
// → 创建适配器 → 添加到 model->loras
llama_set_adapter_lora(ctx, adapter, scale);
// → 将适配器绑定到上下文

// 推理时，计算图构建会检查是否有激活的 LoRA:
// build_lora_mm() 代替常规 mm:
//   如果该层有 LoRA: output = W(x) + lora_B(lora_A(x)) * scale
//   否则: output = W(x)
```

---

## 附录 A：核心函数调用关系图

```
用户代码                          llama.cpp 内部
─────────                        ──────────────
llama_load_model_from_file()
  │
  ├── llama_model_load_from_file_impl()
  │     │
  │     ├── llama_model_loader 构造函数
  │     │     ├── gguf_init_from_file()    ← 解析 GGUF
  │     │     ├── 扫描 tensor 元数据
  │     │     └── 确定文件类型
  │     │
  │     ├── new llama_model(params)
  │     │
  │     ├── model->load_arch(ml)          ← 架构枚举
  │     ├── model->load_hparams(ml)       ← 超参数
  │     ├── model->load_vocab(ml)         ← 词表
  │     └── model->load_tensors(ml)       ← 张量
  │           ├── create_tensor()         ← 分配缓冲区
  │           └── load_all_data()         ← 填充数据
  │
  └── return model

llama_new_context_with_model(model, params)
  │
  ├── new llama_context(model, params)
  │     ├── model->create_memory(params)  ← KV Cache
  │     ├── scheduler = new ggml_backend_sched
  │     └── 初始化 sampler chain
  │
  └── return ctx

llama_decode(ctx, batch)
  │
  ├── model->build_graph(params)          ← 构建计算图
  │     └── llm_build_llama::build_graph()
  │           ├── tok_embd → ... → transformer layers → output
  │           └── 每次调用构建 ggml_cgraph DAG
  │
  ├── ggml_backend_sched_graph_compute(sched, gf)
  │     └── 按拓扑序执行所有张量操作
  │
  └── 返回 logits / embeddings
```

---

## 附录 B：关键常量

```cpp
#define LLAMA_MAX_LAYERS  512   // 最大支持层数
#define LLAMA_MAX_EXPERTS 512   // 最大专家数 (Qwen3 Next)
#define LLAMA_MAX_DEVICES 16    // 最多支持 16 个设备
```

---

> 本文档基于 `llama.cpp` 代码库自动分析生成。所有文件引用路径相对于代码库根目录 `llama.cpp/`。
