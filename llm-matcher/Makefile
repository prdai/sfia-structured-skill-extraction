MODEL_DIR := models
MODEL := $(MODEL_DIR)/qwen2.5-0.5b-instruct-q4_k_m.gguf
MODEL_URL := https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf

.PHONY: model
model: $(MODEL)

$(MODEL):
	mkdir -p $(MODEL_DIR)
	curl -L -o $@ $(MODEL_URL)
