/**
 * YouTube Memory Graph - Main Application
 * 使用 Canvas + d3-force 渲染
 */

// ========================================
// 全局状态
// ========================================

const state = {
    rawData: null,
    tagStats: {},
    currentView: 'bubble',
    selectedTag: null,
    selectedColor: null,

    // Canvas 和 渲染相关
    bubbleCanvas: null,
    bubbleCtx: null,
    bubbleSimulation: null,

    graphCanvas: null,
    graphCtx: null,
    graphSimulation: null,

    // 节点数据
    bubbles: [],
    nodes: [],
    links: [],
    hoveredBubble: null,
    hoveredNode: null,

    // 拖拽状态
    draggedNode: null,
    dragOffset: { x: 0, y: 0 },
    dragStartPos: { x: 0, y: 0 },
    isDragging: false,
    justDragged: false,  // 刚完成拖拽标志

    // 时间范围
    timeRange: { min: null, max: null },
};

// ========================================
// DOM 元素
// ========================================

const elements = {
    bubbleView: document.getElementById('bubbleView'),
    graphView: document.getElementById('graphView'),
    bubbleCanvas: document.getElementById('bubbleCanvas'),
    graphCanvas: document.getElementById('graphCanvas'),
    tooltip: document.getElementById('tooltip'),
    loading: document.getElementById('loading'),
    loadDataBtn: document.getElementById('loadDataBtn'),
    fileInput: document.getElementById('fileInput'),
    backBtn: document.getElementById('backBtn'),
};

// ========================================
// 工具函数
// ========================================

function generateRandomColor() {
    const hue = Math.random() * 360;
    return `hsl(${hue}, 70%, 60%)`;
}

function parseWatchTime(timeStr) {
    if (!timeStr || timeStr === 'Unknown') return new Date();

    try {
        const match = timeStr.match(/(\d{4})年(\d{1,2})月(\d{1,2})日/);
        if (match) {
            const [, year, month, day] = match;
            let hour = 12, minute = 0;

            const timeMatch = timeStr.match(/(上午|下午)(\d{1,2}):(\d{2})/);
            if (timeMatch) {
                const [_, period, h, m] = timeMatch;
                hour = parseInt(h);
                minute = parseInt(m);
                if (period === '下午' && hour !== 12) hour += 12;
                if (period === '上午' && hour === 12) hour = 0;
            }

            return new Date(parseInt(year), parseInt(month) - 1, parseInt(day), hour, minute);
        }
    } catch (e) {
        console.warn('时间解析失败:', timeStr);
    }
    return new Date();
}

function calculateTimeOpacity(watchTime, minTime, maxTime) {
    if (!minTime || !maxTime || minTime.getTime() === maxTime.getTime()) return 1;
    const totalSpan = maxTime - minTime;
    const elapsed = watchTime - minTime;
    const ratio = elapsed / totalSpan;
    return 0.3 + ratio * 0.7;
}

function showLoading(show) {
    elements.loading.classList.toggle('hidden', !show);
}

function switchView(view) {
    state.currentView = view;

    if (view === 'bubble') {
        elements.bubbleView.classList.remove('hidden');
        elements.graphView.classList.add('hidden');
        if (state.graphSimulation) {
            state.graphSimulation.stop();
        }
    } else {
        elements.bubbleView.classList.add('hidden');
        elements.graphView.classList.remove('hidden');
    }
}

// ========================================
// 数据处理
// ========================================

function calculateTagStats(data) {
    const stats = {};

    for (const [videoTitle, info] of Object.entries(data)) {
        if (!Array.isArray(info) || info.length < 3) continue;

        const [tagsStr, url, watchTime] = info;
        if (!tagsStr || !url) continue;

        const tags = tagsStr.split(',').map(t => t.trim()).filter(t => t);

        for (const tag of tags) {
            if (!stats[tag]) {
                stats[tag] = {
                    count: 0,
                    color: generateRandomColor(),
                    videos: []
                };
            }

            stats[tag].count++;
            stats[tag].videos.push({
                title: videoTitle,
                url: url,
                watchTime: watchTime,
                tags: tags
            });
        }
    }

    return stats;
}

// ========================================
// 气泡图 - Canvas 渲染
// ========================================

function initBubbleCanvas() {
    const canvas = elements.bubbleCanvas;
    const container = canvas.parentElement;
    const width = container.clientWidth;
    const height = container.clientHeight || window.innerHeight - 120;

    // 设置 canvas 的实际像素尺寸
    canvas.width = width;
    canvas.height = height;

    state.bubbleCanvas = canvas;
    state.bubbleCtx = canvas.getContext('2d');
}

function getBubbleRadius(count) {
    return Math.min(Math.max(30, 20 + count * 2), 100);
}

function renderBubbleChart() {
    const tags = Object.entries(state.tagStats);
    console.log('统计数据:', tags.length, '个标签');

    if (tags.length === 0) {
        // 显示空状态
        const container = elements.bubbleCanvas;
        container.innerHTML = `
            <div class="empty-state">
                <h2>⚠️ 没有找到标签数据</h2>
                <p>请确保 JSON 文件格式正确，包含有效标签</p>
                <p style="margin-top: 10px; font-size: 12px; color: #888;">
                    期望格式: {"视频标题": ["标签1,标签2", "url", "时间"]}
                </p>
            </div>
        `;
        return;
    }

    initBubbleCanvas();

    const width = state.bubbleCanvas.width;
    const height = state.bubbleCanvas.height;

    // 准备气泡数据
    state.bubbles = tags.map(([name, data], i) => ({
        id: i,
        name: name,
        count: data.count,
        color: data.color,
        r: getBubbleRadius(data.count),
        videos: data.videos,
        x: width / 2 + (Math.random() - 0.5) * 400,
        y: height / 2 + (Math.random() - 0.5) * 400,
        vx: 0,
        vy: 0
    }));

    // 创建力导向模拟
    if (state.bubbleSimulation) {
        state.bubbleSimulation.stop();
    }

    state.bubbleSimulation = d3.forceSimulation(state.bubbles)
        .force('charge', d3.forceManyBody().strength(-80))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(d => d.r + 15))
        .force('boundary', () => {
            // 边界力：阻止气泡超出画布
            state.bubbles.forEach(bubble => {
                const r = bubble.r + 5;
                if (bubble.x < r) bubble.vx += (r - bubble.x) * 0.1;
                if (bubble.x > width - r) bubble.vx += (width - r - bubble.x) * 0.1;
                if (bubble.y < r) bubble.vy += (r - bubble.y) * 0.1;
                if (bubble.y > height - r) bubble.vy += (height - r - bubble.y) * 0.1;
            });
        })
        .alphaDecay(0.02)
        .velocityDecay(0.4)
        .on('tick', drawBubbles);

    // 添加鼠标事件
    state.bubbleCanvas.onmousedown = handleBubbleMouseDown;
    state.bubbleCanvas.onmousemove = handleBubbleMouseMove;
    state.bubbleCanvas.onmouseup = handleBubbleMouseUp;
    state.bubbleCanvas.onmouseleave = handleBubbleMouseUp;
    state.bubbleCanvas.onclick = handleBubbleClick;
}

function drawBubbles() {
    const ctx = state.bubbleCtx;
    const width = state.bubbleCanvas.width;
    const height = state.bubbleCanvas.height;

    // 清空画布
    ctx.clearRect(0, 0, width, height);

    // 绘制气泡
    state.bubbles.forEach(bubble => {
        const isHovered = state.hoveredBubble === bubble;
        const scale = isHovered ? 1.15 : 1;
        const r = bubble.r * scale;

        // 边界检测：确保气泡在画布内
        bubble.x = Math.max(r, Math.min(width - r, bubble.x));
        bubble.y = Math.max(r, Math.min(height - r, bubble.y));

        // 绘制圆形
        ctx.beginPath();
        ctx.arc(bubble.x, bubble.y, r, 0, Math.PI * 2);
        ctx.fillStyle = bubble.color;
        ctx.globalAlpha = isHovered ? 1 : 0.85;
        ctx.fill();
        ctx.globalAlpha = 1;

        // 绘制边框
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = isHovered ? 3 : 2;
        ctx.stroke();

        // 绘制阴影（hover时）
        if (isHovered) {
            ctx.shadowColor = 'rgba(255, 255, 255, 0.5)';
            ctx.shadowBlur = 20;
            ctx.stroke();
            ctx.shadowBlur = 0;
        }

        // 绘制标签文字（增大字体）
        ctx.fillStyle = 'white';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.font = `bold 16px sans-serif`;
        ctx.fillText(bubble.name.substring(0, 6), bubble.x, bubble.y - 8);

        // 绘制数量
        ctx.font = `14px sans-serif`;
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.fillText(`${bubble.count}`, bubble.x, bubble.y + 10);
    });
}

function getBubbleAtPoint(x, y) {
    for (let i = state.bubbles.length - 1; i >= 0; i--) {
        const bubble = state.bubbles[i];
        const dx = x - bubble.x;
        const dy = y - bubble.y;
        if (dx * dx + dy * dy < bubble.r * bubble.r) {
            return bubble;
        }
    }
    return null;
}

function handleBubbleMouseMove(e) {
    const rect = state.bubbleCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // 拖拽中
    if (state.draggedNode) {
        const bubble = state.draggedNode;
        bubble.x = x;
        bubble.y = y;
        bubble.fx = x;
        bubble.fy = y;
        state.bubbleCanvas.style.cursor = 'grabbing';
        drawBubbles();
        return;
    }

    const bubble = getBubbleAtPoint(x, y);
    state.hoveredBubble = bubble;
    state.bubbleCanvas.style.cursor = bubble ? 'grab' : 'default';

    if (bubble) {
        showBubbleTooltip(e, bubble);
        if (state.bubbleSimulation) {
            state.bubbleSimulation.alphaTarget(0);
        }
    } else {
        hideTooltip();
        if (state.bubbleSimulation) {
            state.bubbleSimulation.alphaTarget(0);
        }
    }

    drawBubbles();
}

function handleBubbleMouseDown(e) {
    const rect = state.bubbleCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const bubble = getBubbleAtPoint(x, y);
    if (bubble) {
        state.draggedNode = bubble;
        bubble.fx = bubble.x;
        bubble.fy = bubble.y;
        state.bubbleCanvas.style.cursor = 'grabbing';

        if (state.bubbleSimulation) {
            state.bubbleSimulation.alphaTarget(0.3).restart();
        }
    }
}

function handleBubbleMouseUp(e) {
    if (state.draggedNode) {
        const bubble = state.draggedNode;
        bubble.fx = bubble.x;
        bubble.fy = bubble.y;
        state.draggedNode = null;

        if (state.bubbleSimulation) {
            state.bubbleSimulation.alphaTarget(0);
        }
    }
}

function handleBubbleClick(e) {
    const rect = state.bubbleCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const bubble = getBubbleAtPoint(x, y);
    if (bubble) {
        state.selectedTag = bubble.name;
        state.selectedColor = bubble.color;
        switchView('graph');
        renderKnowledgeGraph(bubble.videos);
    }
}

function showBubbleTooltip(e, bubble) {
    const tooltip = elements.tooltip;

    tooltip.querySelector('.tooltip-title').textContent = bubble.name;
    tooltip.querySelector('.tooltip-channel').textContent = `📹 ${bubble.count} 个视频`;
    tooltip.querySelector('.tooltip-time').textContent = '点击查看详情';
    tooltip.querySelector('.tooltip-link').style.display = 'none';

    state.tooltipVisible = true;
    state.tooltipHovered = false;

    positionTooltip(e);
    tooltip.classList.add('visible');
}

// ========================================
// 知识图谱 - Canvas 渲染
// ========================================

function initGraphCanvas() {
    const canvas = elements.graphCanvas;
    const container = canvas.parentElement;
    const width = container.clientWidth;
    const height = container.clientHeight || window.innerHeight - 120;

    // 设置 canvas 的实际像素尺寸
    canvas.width = width;
    canvas.height = height;

    state.graphCanvas = canvas;
    state.graphCtx = canvas.getContext('2d');
}

function renderKnowledgeGraph(videos) {
    if (!videos || videos.length === 0) return;

    initGraphCanvas();

    const width = state.graphCanvas.width;
    const height = state.graphCanvas.height;

    // 准备节点数据
    state.nodes = videos.map((v, i) => ({
        id: i,
        title: v.title,
        url: v.url,
        watchTime: v.watchTime,
        tags: v.tags,
        x: width / 2 + (Math.random() - 0.5) * 300,
        y: height / 2 + (Math.random() - 0.5) * 300,
        vx: 0,
        vy: 0
    }));

    // 计算时间范围
    const times = videos.map(v => parseWatchTime(v.watchTime));
    state.timeRange.min = d3.min(times);
    state.timeRange.max = d3.max(times);

    // 准备连线
    state.links = [];
    for (let i = 0; i < state.nodes.length; i++) {
        for (let j = i + 1; j < state.nodes.length; j++) {
            const sharedTags = state.nodes[i].tags.filter(t => state.nodes[j].tags.includes(t));
            if (sharedTags.length > 0) {
                state.links.push({
                    source: i,
                    target: j,
                    strength: sharedTags.length
                });
            }
        }
    }

    // 创建力导向模拟
    if (state.graphSimulation) {
        state.graphSimulation.stop();
    }

    state.graphSimulation = d3.forceSimulation(state.nodes)
        .force('charge', d3.forceManyBody().strength(-50))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(15))
        .force('link', d3.forceLink(state.links).id(d => d.id).distance(60))
        .force('boundary', () => {
            // 边界力
            state.nodes.forEach(node => {
                const r = 15;
                if (node.x < r) node.vx += (r - node.x) * 0.1;
                if (node.x > width - r) node.vx += (width - r - node.x) * 0.1;
                if (node.y < r) node.vy += (r - node.y) * 0.1;
                if (node.y > height - r) node.vy += (height - r - node.y) * 0.1;
            });
        })
        .alphaDecay(0.02)
        .velocityDecay(0.4)
        .on('tick', drawGraph);

    // 添加鼠标事件
    setupGraphEvents();
}

function drawGraph() {
    const ctx = state.graphCtx;
    const width = state.graphCanvas.width;
    const height = state.graphCanvas.height;

    // 清空画布
    ctx.clearRect(0, 0, width, height);

    // 绘制连线
    state.links.forEach(link => {
        const source = link.source;
        const target = link.target;
        if (source.x === undefined || target.x === undefined) return;

        ctx.beginPath();
        ctx.moveTo(source.x, source.y);
        ctx.lineTo(target.x, target.y);
        ctx.strokeStyle = `rgba(255, 255, 255, ${0.1 + link.strength * 0.05})`;
        ctx.lineWidth = Math.min(link.strength + 0.5, 3);
        ctx.stroke();
    });

    // 绘制节点
    state.nodes.forEach(node => {
        if (node.x === undefined) return;

        const isHovered = state.hoveredNode === node;
        const isDragged = state.draggedNode === node;
        const opacity = calculateTimeOpacity(parseWatchTime(node.watchTime), state.timeRange.min, state.timeRange.max);
        const r = isHovered || isDragged ? 12 : 8;

        // 颜色
        const baseColor = d3.color(state.selectedColor) || d3.hsl(0, 0.7, 0.6);

        ctx.beginPath();
        ctx.arc(node.x, node.y, r, 0, Math.PI * 2);

        if (opacity < 0.5) {
            ctx.fillStyle = baseColor.copy({opacity: opacity}).formatRgb();
            ctx.shadowColor = baseColor.formatRgb();
            ctx.shadowBlur = 5;
        } else {
            ctx.fillStyle = baseColor.copy({opacity: opacity}).formatRgb();
            ctx.shadowBlur = 0;
        }
        ctx.fill();

        // 边框
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
        ctx.lineWidth = isHovered || isDragged ? 2 : 1;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // hover 或拖拽时显示文字（增大字体）
        if (isHovered || isDragged) {
            ctx.fillStyle = 'white';
            ctx.textAlign = 'left';
            ctx.textBaseline = 'top';
            ctx.font = '14px sans-serif';
            ctx.fillText(node.title.substring(0, 25) + (node.title.length > 25 ? '...' : ''), node.x + 15, node.y - 10);
        }
    });
}

function setupGraphEvents() {
    const canvas = state.graphCanvas;

    canvas.onmousedown = handleGraphMouseDown;
    canvas.onmousemove = handleGraphMouseMove;
    canvas.onmouseup = handleGraphMouseUp;
    canvas.onmouseleave = handleGraphMouseUp;
    canvas.onclick = handleGraphClick;
}

function getNodeAtPoint(x, y) {
    for (let i = state.nodes.length - 1; i >= 0; i--) {
        const node = state.nodes[i];
        if (node.x === undefined) continue;
        const dx = x - node.x;
        const dy = y - node.y;
        if (dx * dx + dy * dy < 144) { // 12px radius
            return node;
        }
    }
    return null;
}

function handleGraphMouseDown(e) {
    const rect = state.graphCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const node = getNodeAtPoint(x, y);
    if (node) {
        state.draggedNode = node;
        state.dragStartPos = { x: x, y: y };  // 记录开始位置
        state.isDragging = false;              // 重置拖拽状态
        state.justDragged = false;             // 新增：刚完成拖拽标志
        state.dragOffset = { x: node.x - x, y: node.y - y };

        // 固定节点位置
        node.fx = node.x;
        node.fy = node.y;

        if (state.graphSimulation) {
            state.graphSimulation.alphaTarget(0.3).restart();
        }

        // 阻止默认行为
        e.preventDefault();
    }
}

function handleGraphMouseMove(e) {
    const rect = state.graphCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // 拖拽中
    if (state.draggedNode) {
        // 检测是否移动超过阈值（5px）
        const dx = x - state.dragStartPos.x;
        const dy = y - state.dragStartPos.y;
        if (Math.sqrt(dx * dx + dy * dy) > 5) {
            state.isDragging = true;  // 标记为真正的拖拽
        }

        state.draggedNode.fx = x + state.dragOffset.x;
        state.draggedNode.fy = y + state.dragOffset.y;
        state.draggedNode.x = state.draggedNode.fx;
        state.draggedNode.y = state.draggedNode.fy;

        state.graphCanvas.style.cursor = 'grabbing';
        drawGraph();
        return;
    }

    const node = getNodeAtPoint(x, y);
    state.hoveredNode = node;
    state.graphCanvas.style.cursor = node ? 'grab' : 'default';

    if (node) {
        showNodeTooltip(e, node);
    } else {
        hideTooltip();
    }

    drawGraph();
}

function handleGraphMouseUp(e) {
    if (state.draggedNode) {
        // 保持节点在当前位置
        const node = state.draggedNode;
        node.fx = node.x;
        node.fy = node.y;

        // 如果确实移动过，标记为刚拖拽过
        if (state.isDragging) {
            state.justDragged = true;
        }

        state.draggedNode = null;
        state.isDragging = false;

        if (state.graphSimulation) {
            state.graphSimulation.alphaTarget(0);
        }

        // 阻止默认行为
        e.preventDefault();
    }
}

function handleGraphClick(e) {
    // 如果刚完成拖拽，不触发点击
    if (state.justDragged) {
        state.justDragged = false;
        return;
    }

    // 如果正在拖拽，不触发点击
    if (state.draggedNode && state.isDragging) {
        return;
    }

    const rect = state.graphCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const node = getNodeAtPoint(x, y);
    if (node && node.url) {
        window.open(node.url, '_blank');
    }
}

function showNodeTooltip(e, node) {
    const tooltip = elements.tooltip;

    tooltip.querySelector('.tooltip-title').textContent = node.title;
    tooltip.querySelector('.tooltip-channel').textContent = `🏷️ ${node.tags.join(', ')}`;
    tooltip.querySelector('.tooltip-time').textContent = `📅 ${node.watchTime}`;
    tooltip.querySelector('.tooltip-hint').textContent = '👆 点击节点跳转视频';

    state.tooltipVisible = true;
    state.tooltipHovered = false;

    positionTooltip(e);
    tooltip.classList.add('visible');
}

// ========================================
// 通用函数
// ========================================

function hideTooltip() {
    elements.tooltip.classList.remove('visible');
}

function positionTooltip(e) {
    const tooltip = elements.tooltip;
    const rect = tooltip.getBoundingClientRect();

    let x = e.clientX + 15;
    let y = e.clientY + 15;

    if (x + rect.width > window.innerWidth) {
        x = e.clientX - rect.width - 15;
    }
    if (y + rect.height > window.innerHeight) {
        y = e.clientY - rect.height - 15;
    }

    tooltip.style.left = `${x}px`;
    tooltip.style.top = `${y}px`;
}

// ========================================
// 数据加载
// ========================================

async function loadData(file) {
    showLoading(true);

    try {
        const text = await file.text();
        console.log('文件内容长度:', text.length);

        const data = JSON.parse(text);
        console.log('JSON 解析成功，总视频数:', Object.keys(data).length);

        state.rawData = data;
        state.tagStats = calculateTagStats(data);
        console.log('标签统计完成，标签种类:', Object.keys(state.tagStats).length);

        renderBubbleChart();
        addStatsBar();

        console.log('渲染完成');

    } catch (error) {
        console.error('数据加载失败:', error);
        alert('数据加载失败！\n\n错误信息: ' + error.message + '\n\n请检查 JSON 文件格式是否正确。');
    } finally {
        showLoading(false);
    }
}

function addStatsBar() {
    const existing = document.querySelector('.stats-bar');
    if (existing) existing.remove();

    const bar = document.createElement('div');
    bar.className = 'stats-bar';
    bar.innerHTML = `
        <p>🏷️ 标签种类: <span>${Object.keys(state.tagStats).length}</span></p>
        <p>📹 有标签视频: <span>${Object.values(state.tagStats).reduce((sum, t) => sum + t.count, 0)}</span></p>
    `;
    document.body.appendChild(bar);
}

// ========================================
// 事件绑定
// ========================================

function init() {
    elements.loadDataBtn.addEventListener('click', () => {
        elements.fileInput.click();
    });

    elements.fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) loadData(file);
    });

    elements.backBtn.addEventListener('click', () => {
        switchView('bubble');
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && state.currentView === 'graph') {
            switchView('bubble');
        }
    });

    window.addEventListener('resize', () => {
        if (state.currentView === 'bubble' && state.rawData) {
            renderBubbleChart();
        } else if (state.currentView === 'graph' && state.selectedTag) {
            renderKnowledgeGraph(state.tagStats[state.selectedTag]?.videos || []);
        }
    });
}

document.addEventListener('DOMContentLoaded', init);
