document.addEventListener('DOMContentLoaded', () => {
    const generateButton = document.getElementById('generateButton');
    const randomButton = document.getElementById('randomButton');
    const promptSuffixInput = document.getElementById('promptSuffix');
    const queuedPromptsList = document.getElementById('queuedPromptsList');
    const generatedImagesContainer = document.getElementById('generatedImagesContainer');
    const captionsContainer = document.getElementById('captionsContainer');

    // 添加一个全局对象来存储文案状态
    const captionStates = {};

    // 添加文案缓存管理
    const captionCache = {
        save: function(taskId, data) {
            try {
                const captions = this.getAll();
                captions[taskId] = {
                    ...data,
                    timestamp: Date.now()
                };
                localStorage.setItem('imageCaptions', JSON.stringify(captions));
            } catch (e) {
                console.error('保存文案到缓存失败:', e);
            }
        },

        getAll: function() {
            try {
                return JSON.parse(localStorage.getItem('imageCaptions')) || {};
            } catch (e) {
                console.error('读取文案缓存失败:', e);
                return {};
            }
        },

        get: function(taskId) {
            const captions = this.getAll();
            return captions[taskId];
        },

        cleanup: function() {
            const captions = this.getAll();
            const now = Date.now();
            const HOURS_48_IN_MS = 48 * 60 * 60 * 1000;
            
            let changed = false;
            Object.keys(captions).forEach(taskId => {
                if (now - captions[taskId].timestamp > HOURS_48_IN_MS) {
                    delete captions[taskId];
                    changed = true;
                }
            });
            
            if (changed) {
                localStorage.setItem('imageCaptions', JSON.stringify(captions));
            }
        }
    };

    // 添加图片缓存管理
    const imageCache = {
        save: function(taskId, imageData) {
            try {
                const images = this.getAll();
                images[taskId] = {
                    ...imageData,
                    timestamp: Date.now()
                };
                localStorage.setItem('generatedImages', JSON.stringify(images));
            } catch (e) {
                console.error('保存图片到缓存失败:', e);
            }
        },

        getAll: function() {
            try {
                return JSON.parse(localStorage.getItem('generatedImages')) || {};
            } catch (e) {
                console.error('读取图片缓存失败:', e);
                return {};
            }
        },

        get: function(taskId) {
            const images = this.getAll();
            return images[taskId];
        },

        cleanup: function() {
            const images = this.getAll();
            const now = Date.now();
            const HOURS_48_IN_MS = 48 * 60 * 60 * 1000;
            
            let changed = false;
            Object.keys(images).forEach(taskId => {
                if (now - images[taskId].timestamp > HOURS_48_IN_MS) {
                    delete images[taskId];
                    changed = true;
                }
            });
            
            if (changed) {
                localStorage.setItem('generatedImages', JSON.stringify(images));
            }
        }
    };

    generateButton.addEventListener('click', () => {
        const promptSuffix = promptSuffixInput.value.trim();
        if (promptSuffix) {
            generateButton.disabled = true;
            fetch('/submit_prompt', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ prompt_suffix: promptSuffix })
            })
            .then(response => response.json())
            .then(data => {
                if (data.message) {
                    promptSuffixInput.value = '';
                    fetchAndUpdateStatus();
                } else if (data.error) {
                    alert("提交失败: " + data.error);
                }
            })
            .finally(() => {
                generateButton.disabled = false;
            });
        } else {
            alert("请输入提示词。");
        }
    });

    randomButton.addEventListener('click', () => {
        randomButton.disabled = true;
        fetch('/random_prompt')
            .then(response => response.json())
            .then(data => {
                if (data.prompt) {
                    promptSuffixInput.value = data.prompt;
                } else if (data.error) {
                    alert("获取随机提示词失败: " + data.error);
                }
            })
            .catch(error => {
                alert("获取随机提示词失败: " + error.message);
            })
            .finally(() => {
                randomButton.disabled = false;
            });
    });

    function fetchAndUpdateStatus() {
        clearTimers();
        fetch('/get_status')
            .then(response => response.json())
            .then(taskStatuses => {
                updateQueuedPrompts(taskStatuses);
                updateGeneratedImages(taskStatuses);
            });
    }

    function updateQueuedPrompts(taskStatuses) {
        queuedPromptsList.innerHTML = '';
        let queuedCount = 0;
        for (const taskId in taskStatuses) {
            if (taskStatuses.hasOwnProperty(taskId) && taskStatuses[taskId].status === 'queued') {
                queuedCount++;
                const listItem = document.createElement('li');
                listItem.textContent = `任务ID: ${taskId} - 排队中`;
                queuedPromptsList.appendChild(listItem);
            }
        }
        if (queuedCount === 0) {
            const listItem = document.createElement('li');
            listItem.textContent = "当前队列为空。";
            queuedPromptsList.appendChild(listItem);
        }
    }

    function updateGeneratedImages(taskStatuses) {
        generatedImagesContainer.innerHTML = '';
        
        const sortedTasks = Object.entries(taskStatuses)
            .map(([taskId, status]) => ({taskId, ...status}))
            .sort((a, b) => {
                const timeA = a.timestamps.end_time || a.timestamps.start_time || 0;
                const timeB = b.timestamps.end_time || b.timestamps.start_time || 0;
                return timeB - timeA;
            });

        for (const task of sortedTasks) {
            const containerDiv = document.createElement('div');
            containerDiv.className = 'image-container';
            containerDiv.setAttribute('data-task-id', task.taskId);
            
            if (task.status === 'completed') {
                const imageUrl = task.image_url;
                if (imageUrl) {
                    // 保存图片到缓存
                    imageCache.save(task.taskId, {
                        url: imageUrl,
                        original_prompt: task.original_prompt
                    });
                    
                    // 创建图片元素
                    const imgElement = document.createElement('img');
                    imgElement.src = imageUrl;
                    imgElement.alt = `生成的图片 任务ID: ${task.taskId}`;
                    containerDiv.appendChild(imgElement);
                    
                    // 添加计时显示
                    const timerDiv = document.createElement('div');
                    timerDiv.className = 'timer';
                    const duration = task.timestamps.end_time - task.timestamps.start_time;
                    timerDiv.textContent = `耗时: ${duration.toFixed(1)}秒`;
                    containerDiv.appendChild(timerDiv);
                    
                    // 添加提示词显示
                    const promptDiv = document.createElement('div');
                    promptDiv.className = 'prompt-text';
                    promptDiv.textContent = task.original_prompt || "未知提示词";
                    containerDiv.appendChild(promptDiv);
                    
                    // 添加文案容器
                    const captionContainer = document.createElement('div');
                    captionContainer.className = 'caption-container';
                    captionContainer.id = `caption-${task.taskId}`;
                    containerDiv.appendChild(captionContainer);
                    
                    // 添加生成文案按钮
                    const captionButton = document.createElement('button');
                    captionButton.className = 'caption-button';
                    captionButton.textContent = '生成文案';
                    captionButton.onclick = () => generateCaption(task.taskId, task.original_prompt, containerDiv);
                    containerDiv.appendChild(captionButton);

                    // 检查并显示缓存的文案
                    const cachedCaption = captionCache.get(task.taskId);
                    if (cachedCaption) {
                        updateCaptionDisplay(captionContainer, cachedCaption.caption);
                    }
                }
            } else if (task.status === 'processing') {
                const processingDiv = document.createElement('div');
                processingDiv.className = 'processing';
                processingDiv.textContent = `${task.original_prompt || "未知提示词"} - 处理中...`;
                containerDiv.appendChild(processingDiv);
                
                if (task.timestamps.start_time) {
                    const timerDiv = document.createElement('div');
                    timerDiv.className = 'timer';
                    const updateTimer = () => {
                        const currentTime = Date.now() / 1000;
                        const elapsed = currentTime - task.timestamps.start_time;
                        timerDiv.textContent = `已用时: ${elapsed.toFixed(1)}秒`;
                    };
                    updateTimer();
                    const timerId = setInterval(updateTimer, 100);
                    containerDiv.setAttribute('data-timer-id', timerId);
                    containerDiv.appendChild(timerDiv);
                }
            } else if (task.status === 'error') {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'error-message';
                const errorMsg = task.image_url && task.image_url.error ? task.image_url.error : "生成图片时发生错误。";
                errorDiv.textContent = `任务ID: ${task.taskId} - 错误: ${errorMsg}`;
                containerDiv.appendChild(errorDiv);
            }

            generatedImagesContainer.appendChild(containerDiv);
        }
        
        if (generatedImagesContainer.children.length === 0) {
            const noImagesDiv = document.createElement('div');
            noImagesDiv.textContent = "暂无生成的图片。";
            generatedImagesContainer.appendChild(noImagesDiv);
        }
    }

    function generateCaption(taskId, originalPrompt, containerDiv) {
        const captionContainer = containerDiv.querySelector(`#caption-${taskId}`);
        if (!captionContainer) return;
        
        captionContainer.innerHTML = '<div class="loading">正在生成文案...</div>';
        
        fetch('/generate_caption', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                task_id: taskId,
                original_prompt: originalPrompt
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.caption) {
                updateCaptionDisplay(captionContainer, data.caption);
                captionCache.save(taskId, {
                    caption: data.caption,
                    original_prompt: originalPrompt
                });
            } else if (data.error) {
                captionContainer.innerHTML = `<div class="error-message">生成失败: ${data.error}</div>`;
            }
        })
        .catch(error => {
            captionContainer.innerHTML = `<div class="error-message">生成失败: ${error.message}</div>`;
        });
    }

    function updateCaptionDisplay(container, caption) {
        container.innerHTML = `
            <div class="caption-section">
                <div class="caption-header">
                    <span class="section-label">标题</span>
                    <button class="copy-button" data-text="${encodeURIComponent(caption.title)}">复制</button>
                </div>
                <div class="caption-text">${caption.title}</div>
            </div>
            <div class="caption-section">
                <div class="caption-header">
                    <span class="section-label">正文</span>
                    <button class="copy-button" data-text="${encodeURIComponent(caption.content)}">复制</button>
                </div>
                <div class="caption-text">${caption.content}</div>
            </div>
        `;
        
        container.querySelectorAll('.copy-button').forEach(button => {
            button.addEventListener('click', function() {
                const textToCopy = decodeURIComponent(this.getAttribute('data-text'));
                copyText(textToCopy);
            });
        });
    }

    function copyText(text) {
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text)
                .then(() => showCopyTooltip('已复制'))
                .catch(err => {
                    console.error('复制失败:', err);
                    showCopyTooltip('复制失败');
                    fallbackCopyText(text);
                });
        } else {
            fallbackCopyText(text);
        }
    }

    function fallbackCopyText(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        
        try {
            textarea.select();
            document.execCommand('copy');
            showCopyTooltip('已复制');
        } catch (err) {
            console.error('复制失败:', err);
            showCopyTooltip('复制失败');
        } finally {
            document.body.removeChild(textarea);
        }
    }

    function showCopyTooltip(message) {
        const tooltip = document.createElement('div');
        tooltip.className = 'copy-tooltip';
        tooltip.textContent = message;
        document.body.appendChild(tooltip);
        
        setTimeout(() => {
            tooltip.remove();
        }, 2000);
    }

    function clearTimers() {
        const containers = generatedImagesContainer.getElementsByClassName('image-container');
        for (const container of containers) {
            const timerId = container.getAttribute('data-timer-id');
            if (timerId) {
                clearInterval(Number(timerId));
            }
        }
    }

    // 添加定期清理缓存的函数
    function cleanupCaches() {
        captionCache.cleanup();
        imageCache.cleanup();
    }

    // 每小时检查一次缓存
    setInterval(cleanupCaches, 60 * 60 * 1000);
    
    // 初始化时也清理一次
    cleanupCaches();

    setInterval(fetchAndUpdateStatus, 5000);
    fetchAndUpdateStatus();
});