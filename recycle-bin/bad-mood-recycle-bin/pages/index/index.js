// pages/index/index.js —— 坏情绪回收站 · 主场景逻辑 v20（暗色科幻 · 四段时序）
// 纯前端模拟：无后端 / 无登录 / 无数据库；Storage 只用来记录"是否已看过首次引导"
// 严格四段交互时序（背景全程静止，禁止背景抖动）：
//   ① 页面加载 → 图1「待机微笑」从屏幕下方浮入中心，停住等待点击
//   ② 点击机器人 → 图2「认真倾听」 + 弹出情绪输入框
//   ③ 提交回收   → 保留图2，仅机器人本体抖动（背景不动）
//   ④ 抖动结束   → 图3「比心」 + 飘散能量气泡 + 触发礼物藏品掉落
// 宝箱 / 积分 / 数字藏品 / 优惠券 业务逻辑全部保留，本次仅改图片切换 + 动画时序。

const GUIDE_KEY = 'bmb_guide_shown_v1';

// 情绪识别规则（关键词匹配，纯前端模拟）
const MOOD_RULES = [
  {
    type: 'tired',
    words: ['累', '疲惫', '困', '乏', '没力气', '没劲', '加班', '熬夜', '虚脱', '透支', '不想动', '精疲力尽', '好累', '累死', '疲惫不堪']
  },
  {
    type: 'sad',
    words: ['委屈', '难过', '伤心', '哭', '想哭', '心酸', '难受', '抑郁', '失落', '想家', '眼泪', '哽咽', '憋屈', '被冤枉', '不被理解']
  },
  {
    type: 'angry',
    words: ['生气', '愤怒', '气死', '火大', '暴躁', '烦', '讨厌', '恨', '抓狂', '恼火', '憋火', '不爽', '炸', '烦躁', '烦死', '暴怒']
  }
];

// 成长阶段随机奖励池：回收成功后机器人头顶弹出的温暖反馈
// title = 短激励词；desc = 核心大文案（绿色高亮、放大显示）
const REWARD_POOL = [
  { icon: '🌱', title: '回收成功', desc: '坏情绪已回收，继续向前走' },
  { icon: '🌿', title: '轻松一点', desc: '把沉重交给 Nova，你值得松口气' },
  { icon: '✨', title: '已收好', desc: '这一份情绪，已安全封存' },
  { icon: '💚', title: '温柔待己', desc: '愿意倾诉，就已经很勇敢了' },
  { icon: '🌟', title: '翻篇啦', desc: '坏心情留在回收站，向前看' },
  { icon: '🤍', title: '抱抱你', desc: '此刻的难过，Nova 都接住了' }
];

// 语音输入演示样本（真实识别需接后端/云函数，演示版直接回填）
const VOICE_SAMPLES = [
  '今天开会开了好久，好累……',
  '有点委屈，感觉自己不被理解。',
  '刚跟人吵架了，气得不行。',
  '加班到很晚，精疲力尽。',
  '想到一些事，心里闷闷的难受。'
];

// v13.2 数字藏品（藏品馆）：永久收藏，不消耗，纯纪念，无交易，不能买卖
//   —— 是用户情绪记录的勋章，按「累计回收次数」点亮（need 即所需回收次数）
//   —— 注意：NOT 用养分兑换，仅作纪念徽章
const BADGES = [
  {
    id: 'sprout',
    name: '粒子残核',
    icon: '✷',
    img: '/images/badge_particle_core.png',
    story: '第一缕从坏情绪里提炼出的微光，被封进核壳成为「粒子残核」——情绪疗愈的起点，永不消散。',
    need: 1
  },
  { id: 'clover',  name: '青苗勋章', icon: '🌿', story: '情绪慢慢长出新芽，你开始学会与低落共处。', need: 5 },
  { id: 'bloom',   name: '暖心花语', icon: '🌸', story: '一次次回收之后，心里悄悄开出了温柔的花。', need: 10 },
  { id: 'star',    name: '星光守护', icon: '🌟', story: '二十次倾诉，星光替你照亮那些难熬的夜。', need: 20 },
  { id: 'crystal', name: '能量水晶', icon: '💎', story: '三十五次疗愈，负面情绪凝成剔透的水晶。', need: 35 },
  { id: 'crown',   name: '情绪园丁', icon: '👑', story: '五十次回收，你已是自己心田的园丁。', need: 50 }
];

// v13.2 宝箱页面优惠券：消耗养分兑换，一次性核销，线下商家福利
const COUPONS = [
  { id: 'coffee', name: '减压咖啡券', merchant: '悦己咖啡', desc: '合作门店单杯立减 ¥8',   cost: 60 },
  { id: 'book',   name: '静心书店券', merchant: '慢读书店', desc: '合作书店满 ¥30 减 ¥10', cost: 90 },
  { id: 'spa',    name: '舒缓按摩券', merchant: '释压工坊', desc: '合作门店体验 5 折',      cost: 140 }
];

// v13.2 持久化 key
const ENERGY_KEY  = 'bmb_energy_v1';   // 跨会话累计「养分」
const RECYCLE_KEY = 'bmb_recycle_v1';  // 跨会话累计回收次数（决定徽章是否点亮）
const COUPON_KEY  = 'bmb_coupons_v1';  // 已核销优惠券 [{id, code}]

Page({
  data: {
    // 首次引导
    showGuide: false,
    // 机器人在首屏的四态：idle 待机微笑 | listen 认真倾听 | shaking 抖动中 | heart 比心
    // 注意：机器人全程固定在屏幕中心（.robot-stage 不再位移），只有立绘切换 + 本体动画
    robotState: 'idle',
    // 入场相位（仅用于兼容 .intro--* 灯光类，新版时序不依赖 lamp/ask/greeting 分支）
    enterPhase: 'idle',
    // 当前机器人立绘资源（idle/listen/heart）
    robotImage: '/images/robot_idle.png',
    robotPose: 'idle',
    // 首页入场动画标记：仅首次进入播放一次"从下方浮入就位"，不影响任何业务逻辑
    introActive: true,
    // 眨眼（greet-sparkles）和挠头（greet-hand）的触发开关
    blinkActive: false,
    patActive: false,
    // 回收成功时胸口发射的淡绿粒子
    particles: [],
    // 交互面板
    panelVisible: false,
    // v12.10 独立"询问"步骤：机器人到中央做完反应后，先冒出问话气泡 +
    // "开始倾诉"按钮，作为明确可感知的"让用户录入坏情绪"步骤；用户点击
    // "开始倾诉"后才滑出真正的录入框（panelVisible）。askVisible 控制气泡。
    askVisible: false,
    submitting: false,
    inputText: '',
    // 语音输入（演示）
    recording: false,
    // 回收数据
    energy: 0,
    recycleCount: 0,
    // 当前情绪类型：normal | tired | sad | angry
    moodType: 'normal',
    // 动画状态
    suckAnim: false,
    floatEnergy: false,
    rewardVisible: false,
    reward: {},
    /* ----- v12.8 礼物掉落（新增字段，不修改旧 data） -----
       giftItems: 礼物队列，每项 {id, type, icon, x, top, delay, value}
       _giftDropTimer / _giftCleanTimer: 内部清理用，存到 this 上，不进 data 避免触发重渲染 */
    giftItems: [],

    /* ----- v13.2 宝箱：养分 + 数字藏品（永久纪念）+ 优惠券 -----
       collectedEnergy   跨会话累计养分（持久化）
       recycleCount      跨会话累计回收次数（持久化，决定徽章点亮）
       redeemedCoupons   已核销优惠券 [{id, code}]（持久化）
       chestOpen         面板是否打开
       chestTab          'badge' 数字藏品 | 'coupon' 优惠券
       chestBounce       收集到能量时宝箱弹一下
       badgeItems        派生：含 owned（回收次数是否达标）
       couponItems       派生：含 redeemed / code / canAfford
       badgeModal        点击徽章后的放大弹窗数据，null 表示关闭 */
    collectedEnergy: 0,
    recycleCount: 0,
    redeemedCoupons: [],
    chestOpen: false,
    chestTab: 'badge',
    chestBounce: false,
    badgeItems: [],
    couponItems: [],
    badgeModal: null
  },

  onLoad() {
    // 开机直接进入首页：机器人 busy 待命、安静待命（按最新需求不再弹引导遮罩）
    // 注意：v6 移除了自动 playIntro，首次进入直接呈现 busy 状态的机器人

    // v13.2 宝箱：跨会话恢复养分、回收次数、已核销优惠券
    const savedEnergy  = parseInt(wx.getStorageSync(ENERGY_KEY) || '0', 10);
    const savedRecycle = parseInt(wx.getStorageSync(RECYCLE_KEY) || '0', 10);
    const savedCoupons = wx.getStorageSync(COUPON_KEY);
    this.setData({
      collectedEnergy: isNaN(savedEnergy) ? 0 : savedEnergy,
      recycleCount: isNaN(savedRecycle) ? 0 : savedRecycle,
      redeemedCoupons: Array.isArray(savedCoupons) ? savedCoupons : []
    });

    // v20 时序：礼物掉落不再依赖"回原位"钩子（机器人始终居中，无位移）。
    // 改为在 onSubmit 抖动结束、切到「比心」态时直接调 _dropGift，与时序④严格对齐。

    // 首页入场动画：1.2s 后清除 intro 类，交还给待机呼吸动画（纯展示层，不触碰任何业务逻辑）
    setTimeout(() => this.setData({ introActive: false }), 1200);
  },

  onUnload() {
    if (this._voiceTimer) clearTimeout(this._voiceTimer);
    if (this._rewardTimer) clearTimeout(this._rewardTimer);
    if (this._clickTimers) this._clickTimers.forEach(t => clearTimeout(t));
    /* v12.7 追加：清理藤蔓/礼物相关定时器（不改动原有清理逻辑） */
    if (this._giftDropTimer) clearTimeout(this._giftDropTimer);
    if (this._giftCleanTimer) clearTimeout(this._giftCleanTimer);
    /* v13 粒子定时器 */
    if (this._particleTimer) clearTimeout(this._particleTimer);
    if (this._chestBounceTimer) clearTimeout(this._chestBounceTimer);
  },

  // 防止冒泡的空方法
  noop() {},

  // ---------- 首次引导 ----------
  onGuideClose() {
    wx.setStorageSync(GUIDE_KEY, true);
    this.setData({ showGuide: false });
    // 不需要启动动画，机器人已在 busy 状态待命
  },

  // 演示工具：长按底部文案可重置首次引导，便于反复验证"仅第一次弹出"
  onResetGuide() {
    wx.removeStorageSync(GUIDE_KEY);
    this.setData({ showGuide: true });
    wx.showToast({ title: '已重置首次引导，可重新验证（演示用）', icon: 'none', duration: 1800 });
  },

  // ---------- v20 时序②：点击机器人 → 图2「认真倾听」+ 弹出情绪输入框 ----------
  onTapRobot() {
    // 多重防护，避免动画/录入期间被误点
    if (this.data.showGuide) return;
    if (this.data.panelVisible || this.data.askVisible) return;
    if (this.data.submitting) return;
    if (this.data.introActive) return;          // 入场动画期间禁点
    if (this.data.robotState !== 'idle') return; // 仅待机态可点

    // 清理上一次未完成的定时器（防止用户连续点）
    if (this._clickTimers) this._clickTimers.forEach(t => clearTimeout(t));
    this._clickTimers = [];

    const T = (ms, fn) => {
      const t = setTimeout(fn, ms);
      this._clickTimers.push(t);
      return t;
    };

    // ① 切换为图2「认真倾听」，先冒出询问气泡
    this.setData({
      robotState: 'listen',
      robotImage: '/images/robot_listen.png',
      robotPose: 'listen',
      askVisible: true
    });
    // ② 稍作停顿（约 450ms）再滑出输入面板，让"机器人反应 → 询问气泡 → 录入框"衔接清晰
    T(450, () => {
      if (!this.data.submitting && this.data.robotState === 'listen') {
        this.setData({ panelVisible: true });
      }
    });
  },

  // ---------- 关闭交互面板 ----------
  onClosePanel() {
    if (this.data.submitting) return;
    if (!this.data.panelVisible) return;
    this.setData({ panelVisible: false, askVisible: false });
    // 面板关闭后，机器人回到待机态（图1 待机微笑），背景始终静止、不位移
    setTimeout(() => {
      if (!this.data.panelVisible && !this.data.submitting) {
        this.setData({
          robotState: 'idle',
          enterPhase: 'idle',
          robotImage: '/images/robot_idle.png',
          robotPose: 'idle'
        });
      }
    }, 340);
  },

  // ---------- v12.10 询问步骤：从气泡进入录入框 ----------
  onStartRecord() {
    if (this.data.submitting) return;
    if (!this.data.askVisible) return;
    this.setData({
      askVisible: false,
      panelVisible: true
    });
  },

  // ---------- v12.10 询问步骤：用户选择"先不了"，机器人退回待机态 ----------
  onDismissAsk() {
    if (!this.data.askVisible) return;
    this.setData({
      askVisible: false,
      robotState: 'idle',
      enterPhase: 'idle',
      robotImage: '/images/robot_idle.png',
      robotPose: 'idle'
    });
  },

  // ---------- 输入 ----------
  onInput(e) {
    this.setData({ inputText: e.detail.value });
  },

  // ---------- 语音输入（演示：模拟录音与识别） ----------
  onVoiceStart() {
    if (this.data.submitting) return;
    this.setData({ recording: true });
    this._voiceTimer = setTimeout(() => {
      if (this.data.recording) this._finishVoice();
    }, 6000);
  },

  onVoiceEnd() {
    if (this.data.recording) this._finishVoice();
  },

  _finishVoice() {
    if (this._voiceTimer) {
      clearTimeout(this._voiceTimer);
      this._voiceTimer = null;
    }
    this.setData({ recording: false });
    const sample = VOICE_SAMPLES[Math.floor(Math.random() * VOICE_SAMPLES.length)];
    setTimeout(() => {
      this.setData({ inputText: sample });
      wx.showToast({ title: '语音识别完成（演示）', icon: 'none' });
    }, 700);
  },

  // ---------- v20 确认回收：时序③→④（保留图2抖动 → 切图3比心 + 能量气泡 + 礼物掉落） ----------
  onSubmit() {
    const text = (this.data.inputText || '').trim();
    if (this.data.submitting) return;
    if (!text) {
      wx.showToast({ title: '先写下或说出你的坏心情哦', icon: 'none' });
      return;
    }

    const moodType = this._detectMood(text);
    this.setData({
      submitting: true,
      panelVisible: false,
      askVisible: false,
      inputText: ''
    });

    const T = (ms) => new Promise((r) => setTimeout(r, ms));

    (async () => {
      // ① 等输入面板收起
      await T(320);

      // ②【时序③】保留图2「认真倾听」，仅机器人本体播放抖动动画（背景完全静止）
      //    robotState='shaking' → CSS `.scene--shaking .robot-character` 只抖机器人本体
      this.setData({ robotState: 'shaking' });
      await T(550);   // 与 robotShakeGentle 时长一致

      // ③【时序④】抖动结束：切换图3「比心」，播放飘散能量气泡特效
      this.setData({
        robotState: 'heart',
        robotPose: 'heart',
        robotImage: '/images/robot_heart.png'
      });

      // ④ 发放情绪养分（业务逻辑不变）：数值 +20、本地缓存、宝箱弹动、胸口发射淡绿粒子
      const recycleCount = this.data.recycleCount + 1;
      const energy = this.data.energy + 10;
      const collectedEnergy = this.data.collectedEnergy + 20;
      wx.setStorageSync(ENERGY_KEY, collectedEnergy);
      wx.setStorageSync(RECYCLE_KEY, recycleCount);
      this.setData({
        recycleCount,
        energy,
        moodType,
        collectedEnergy,
        floatEnergy: true,
        chestBounce: true
      });
      this._emitParticles();
      this._dropReward();
      if (this._chestBounceTimer) clearTimeout(this._chestBounceTimer);
      this._chestBounceTimer = setTimeout(() => this.setData({ chestBounce: false }), 420);

      // ⑤ 触发礼物藏品掉落（飘散的能量气泡 = 可收集的能量球，环绕机器人周边飘落）
      this._dropGift(recycleCount);

      // ⑥ 短暂停留，让用户看到比心 + 能量气泡 + 粒子
      await T(1100);
      this.setData({ floatEnergy: false });

      // ⑦【关键】机器人保持图3「比心」，直到能量气泡（礼物）被收集或超时清理后
      //    才回到图1 待机微笑。这样"能量气泡掉落期间 = 图3"，与需求严格一致；
      //    机器人不位移，背景始终静止。回待机的动作由 _settleRobot 在礼物清空时触发。
    })();
  },

  // ---------- v13 回收成功：从胸口向外发射淡绿粒子 ----------
  _emitParticles() {
    const count = 12;
    const now = Date.now();
    const particles = [];
    for (let i = 0; i < count; i++) {
      const angle = (360 / count) * i + Math.random() * 24 - 12; // 均匀散开 ±12°
      const delay = Math.floor(Math.random() * 180);
      particles.push({
        id: `${now}-${i}`,
        angle,
        delay
      });
    }
    this.setData({ particles });
    // 粒子动画约 1.2s，结束后清空
    if (this._particleTimer) clearTimeout(this._particleTimer);
    this._particleTimer = setTimeout(() => {
      this.setData({ particles: [] });
    }, 1400);
  },

  // 情绪识别（关键词匹配）
  _detectMood(text) {
    for (let i = 0; i < MOOD_RULES.length; i++) {
      const rule = MOOD_RULES[i];
      for (let j = 0; j < rule.words.length; j++) {
        if (text.indexOf(rule.words[j]) > -1) return rule.type;
      }
    }
    return 'normal';
  },

  // 随机奖励
  _dropReward() {
    const reward = REWARD_POOL[Math.floor(Math.random() * REWARD_POOL.length)];
    this.setData({ reward, rewardVisible: true });
    if (this._rewardTimer) clearTimeout(this._rewardTimer);
    this._rewardTimer = setTimeout(() => {
      this.setData({ rewardVisible: false });
    }, 3000);
  },

  /* ============================================================
     v12.9 新增：能量球掉落（藤蔓逻辑已移除，礼物改为可收集能量球）
     行为：
       - 随机选 1~3 个能量球（medal/flower/heart/cloud 视觉区分）
       - 以机器人中心为圆心做环形分布（避开机器人身体，悬浮在其四周）
       - 每个球带 value（5/10/15 正能量），用户点击后收集进宝箱
       - 球悬浮约 6s，未点击则淡出自动清理，避免数组无限增长
     ============================================================ */
  _dropGift(seed) {
    // 能量球图标池（与 reward 池视觉一致）
    const TYPES = [
      { type: 'medal',  icon: '✦' },
      { type: 'flower', icon: '❀' },
      { type: 'heart',  icon: '♡' },
      { type: 'cloud',  icon: '☁' }
    ];
    // 能量值池：偏向 10，偶尔 5 / 15
    const VALUES = [5, 10, 10, 15];
    const n = 1 + Math.floor(Math.random() * 3); // 1~3
    const now = Date.now();
    const items = [];
    for (let i = 0; i < n; i++) {
      const t = TYPES[Math.floor(Math.random() * TYPES.length)];
      // 环形分布：以机器人中心为圆心，让能量球悬浮在机器人"周边"而非身上
      // 注意：gift-layer 是 .robot-stage 的子节点，下面的 left%/top% 是
      // 相对 robot-stage 盒子（≈机器人本体）的坐标，故圆心 (50, 63) 即"机器
      // 人身边"。能量球随机器人移动，回原位后释放即环绕归位后的机器人。
      // 半径 34%~42%（水平）、垂直压缩到 0.62 倍，确保落在身体外圈
      const ang = Math.random() * Math.PI * 2;       // 0~360° 任意方向
      const R   = 34 + Math.random() * 8;            // 水平半径 34%~42%
      const Ry  = R * 0.62;                          // 垂直半径（横向压缩，避免过散）
      const cx = 50, cy = 63;                        // 机器人中心（left% / top%）
      const x   = Math.max(12, Math.min(88, cx + R  * Math.cos(ang)));
      const top = Math.max(24, Math.min(86, cy + Ry * Math.sin(ang)));
      items.push({
        id: `${now}-${i}-${Math.floor(Math.random() * 99999)}`,
        type: t.type,
        icon: t.icon,
        x,
        top,
        value: VALUES[Math.floor(Math.random() * VALUES.length)],
        delay: i * (350 + Math.floor(Math.random() * 300)) // 0ms / 350~650 / 700~1100 ...
      });
    }
    const exist = (this.data && this.data.giftItems) || [];
    const merged = exist.concat(items);
    this.setData({ giftItems: merged });

    // 6.5s 后清理过期能量球（防止无限增长；此 setData 不带 recycleCount，不会触发钩子）
    if (this._giftCleanTimer) clearTimeout(this._giftCleanTimer);
    this._giftCleanTimer = setTimeout(() => {
      const cur = (this.data && this.data.giftItems) || [];
      // 仅保留距今 6.5s 内生成（id 第一段为 timestamp）的项
      const remaining = cur.filter(g => {
        const ts = parseInt(g.id.split('-')[0], 10);
        return (Date.now() - ts) < 6500;
      });
      this.setData({ giftItems: remaining });
      // 若能量气泡全部超时清理完，机器人回到图1 待机（此时已无图3 比心必要）
      if (remaining.length === 0) this._settleRobot();
    }, 6500);
  },

  /* ============================================================
     v12.9 收集能量球：点击后飞入宝箱
     - 标记 _fly 触发"飞向宝箱"动画，480ms 后从队列移除
     - 累加 collectedEnergy 并持久化，宝箱弹一下
     - 全部收集/清理后调用 _settleRobot 让机器人回到图1 待机
     ============================================================ */
  onCollectGift(e) {
    const id = e.currentTarget.dataset.id;
    const items = this.data.giftItems || [];
    const idx = items.findIndex(g => g.id === id);
    if (idx < 0) return;
    const item = items[idx];
    if (item._fly) return; // 正在收集，忽略重复点击

    // 标记飞入中（触发 CSS 飞向宝箱动画），不直接删除
    const next = items.slice();
    next[idx] = Object.assign({}, item, { _fly: true });
    const val = item.value || 10;
    const collectedEnergy = this.data.collectedEnergy + val;
    this.setData({ giftItems: next, collectedEnergy, chestBounce: true });
    wx.setStorageSync(ENERGY_KEY, collectedEnergy);

    // 宝箱弹一下
    if (this._chestBounceTimer) clearTimeout(this._chestBounceTimer);
    this._chestBounceTimer = setTimeout(() => this.setData({ chestBounce: false }), 420);

    // 动画结束后从队列移除；若已全部收集完，机器人回到图1 待机
    setTimeout(() => {
      const cur = (this.data.giftItems || []).filter(g => g.id !== id);
      this.setData({ giftItems: cur });
      if (cur.length === 0) this._settleRobot();
    }, 480);
  },

  /* ============================================================
     v20 机器人落定：能量气泡（礼物）清空后，从图3「比心」回到图1「待机微笑」。
     仅当当前仍处于 heart 态、且礼物队列已空时触发，避免误回退。
     机器人不位移、背景始终静止。
     ============================================================ */
  _settleRobot() {
    if (this.data.robotState !== 'heart') return;
    if (this.data.giftItems && this.data.giftItems.length > 0) return;
    this.setData({
      submitting: false,
      robotState: 'idle',
      enterPhase: 'idle',
      robotImage: '/images/robot_idle.png',
      robotPose: 'idle'
    });
  },

  /* ============================================================
     v13.2 宝箱面板：数字藏品（永久纪念） + 优惠券（消耗养分）
     ============================================================ */
  onOpenChest() {
    this.setData({
      chestOpen: true,
      chestTab: 'badge',
      badgeItems: this._syncBadges(),
      couponItems: this._syncCoupons()
    });
  },
  onCloseChest() {
    this.setData({ chestOpen: false, badgeModal: null });
  },

  // 切换 数字藏品 / 优惠券 标签
  onSwitchTab(e) {
    const tab = e.currentTarget.dataset.tab;
    if (tab === this.data.chestTab) return;
    this.setData({ chestTab: tab });
  },

  // 派生数字藏品视图：按累计回收次数判断「是否点亮」
  _syncBadges() {
    const count = this.data.recycleCount || 0;
    return BADGES.map(b => ({
      id: b.id,
      name: b.name,
      icon: b.icon,
      img: b.img || '',
      story: b.story || '',
      need: b.need,
      owned: count >= b.need
    }));
  },

  // 派生优惠券视图：是否核销 / 能否兑换
  _syncCoupons() {
    const redeemed = this.data.redeemedCoupons || [];
    const energy = this.data.collectedEnergy || 0;
    return COUPONS.map(c => {
      const r = redeemed.find(x => x.id === c.id);
      return {
        id: c.id,
        name: c.name,
        merchant: c.merchant,
        desc: c.desc,
        cost: c.cost,
        redeemed: !!r,
        code: r ? r.code : '',
        canAfford: energy >= c.cost
      };
    });
  },

  // 点击徽章 → 放大弹窗，让用户清楚看到徽章细节
  onTapBadge(e) {
    const id = e.currentTarget.dataset.id;
    const b = BADGES.find(x => x.id === id);
    if (!b) return;
    const owned = (this.data.recycleCount || 0) >= b.need;
    this.setData({
      badgeModal: {
        name: b.name,
        icon: b.icon,
        img: b.img || '',
        story: b.story || '',
        owned
      }
    });
  },
  onCloseBadge() {
    this.setData({ badgeModal: null });
  },

  // 优惠券：消耗养分兑换，一次性核销
  onRedeemCoupon(e) {
    const id = e.currentTarget.dataset.id;
    const c = COUPONS.find(x => x.id === id);
    if (!c) return;
    const redeemed = this.data.redeemedCoupons || [];
    if (redeemed.find(x => x.id === id)) return; // 已核销
    if (this.data.collectedEnergy < c.cost) {
      wx.showToast({ title: '养分不足，再回收几次吧', icon: 'none' });
      return;
    }
    const collectedEnergy = this.data.collectedEnergy - c.cost;
    const code = this._genCode();
    const newRedeemed = redeemed.concat([{ id, code }]);
    wx.setStorageSync(ENERGY_KEY, collectedEnergy);
    wx.setStorageSync(COUPON_KEY, newRedeemed);
    this.setData({
      collectedEnergy,
      redeemedCoupons: newRedeemed,
      couponItems: this._syncCoupons()
    });
    wx.showToast({ title: `已兑换「${c.name}」`, icon: 'success' });
  },

  // 生成一次性核销码（形如 AB12-CD34）
  _genCode() {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let s = '';
    for (let i = 0; i < 8; i++) s += chars[Math.floor(Math.random() * chars.length)];
    return s.slice(0, 4) + '-' + s.slice(4);
  }
});
