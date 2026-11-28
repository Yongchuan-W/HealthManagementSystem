/* ==========================================================
   异地家庭慢病照护增强模块（大创立项聚焦版）
   职责：
   1. 14 天「异地求学子女 + 62岁高血压父亲」完整示例档案初始化与一键重置
   2. 长辈极简录入模式（大字防误触 + 血压计拍照识别/模拟 + 口语解析）
   3. 写前安全校验（生理边界 + 近 7 天历史基线突变检测 + 语音播报核对）
   4. 首屏异地家庭慢病协同看板（14 天血压 SVG 趋势 + 状态流转任务 + 异步周报）
   5. 本地可溯源权威指南检索（离线/免登录与在线大模型一致的引用展示）
   ========================================================== */
(function () {
  'use strict';

  const LOCAL_GUIDELINES = [
    {
      id: 'G-HTN-01',
      source: '《中国高血压防治指南（2024年修订版）》',
      title: '家庭自测血压诊断与控制目标',
      keywords: ['血压', '高血压', '135', '85', '140', '90', '爸爸', '父母', '偏高', '达标'],
      summary: '家庭自测血压平均值 ≥135/85 mmHg 提示血压偏高（对应诊室 ≥140/90）；一般高血压患者家庭血压目标通常低于 135/85 mmHg。'
    },
    {
      id: 'G-HTN-02',
      source: '《中国高血压防治指南（2024年修订版）》',
      title: '规范家庭血压测量与复测要点',
      keywords: ['测血压', '测量', '晨起', '复测', '血压计', '波动', '不准'],
      summary: '测量前安静休息 5 分钟，上臂与心脏齐平；早晚各测 2–3 次取均值，并同步记录测量时段与服药状态。'
    },
    {
      id: 'G-HTN-03',
      source: '《中国高血压防治指南（2024年修订版）》',
      title: '降压药依从性与漏服处理原则',
      keywords: ['降压药', '服药', '漏服', '忘吃', '氨氯地平', '吃药', '停药', '用药'],
      summary: '切勿自行停药或加倍补服；疑似漏服应按说明书或咨询医生/药师处理，并由家属建立服药核对提醒。'
    },
    {
      id: 'G-HTN-04',
      source: '《中国高血压防治指南（2024年修订版）》',
      title: '血压急症警戒红线（≥180/110）',
      keywords: ['180', '110', '头晕', '头痛', '胸闷', '胸痛', '心慌', '急诊', '就医'],
      summary: '若血压持续 ≥180/110 mmHg，或伴头痛、胸痛、视物模糊、肢体麻木等症状，必须立即前往医院急诊。'
    },
    {
      id: 'G-HTN-05',
      source: '《中国高血压防治指南（2024年修订版）》',
      title: '高血压日常控盐与膳食干预',
      keywords: ['盐', '咸', '饮食', '吃', '蔬菜', '早餐', '午餐', '晚餐', '食谱', '控盐'],
      summary: '每日食盐摄入逐步控制在 <5 克，减少腌菜、卤味和隐形盐；每餐保证新鲜蔬菜与适量优质蛋白。'
    },
    {
      id: 'G-SPORT-01',
      source: '《全民健身指南》/ WHO 身体活动指南',
      title: '规律有氧运动与血压安全边界',
      keywords: ['运动', '跑步', '快走', '散步', '锻炼', '步数', '久坐'],
      summary: '成人每周建议累计 150 分钟中等强度有氧运动；血压波动偏高（≥160/100）时应先稳压再恢复运动。'
    },
    {
      id: 'G-BMI-01',
      source: '《成人体重判定》（WS/T 428-2013）',
      title: '中国成人 BMI 参考范围',
      keywords: ['bmi', '体重', '减肥', '减脂', '超重', '肥胖'],
      summary: '中国成人正常 BMI 区间为 18.5–23.9 kg/m²，超重者温和控制每日 300–500 kcal 热量缺口更可持续。'
    },
    {
      id: 'G-GLU-01',
      source: '《中国2型糖尿病防治指南（2020年版）》',
      title: '空腹血糖参考区间',
      keywords: ['血糖', '糖尿病', '妈妈', '空腹'],
      summary: '正常空腹血糖参考范围为 3.9–6.1 mmol/L，6.1–6.9 提示空腹血糖受损，建议定期复查并控制精制碳水。'
    },
    {
      id: 'G-SLEEP-01',
      source: '《健康中国行动（2019—2030年）》',
      title: '成人规律睡眠建议',
      keywords: ['睡眠', '失眠', '熬夜', '早醒'],
      summary: '倡导成人每日平均睡眠 7–8 小时，作息紊乱会放大晨起血压波动。'
    },
    {
      id: 'G-SAFE-01',
      source: '系统医疗安全合规边界',
      title: '非医疗诊断与处方禁区声明',
      keywords: ['诊断', '治病', '处方', '剂量'],
      summary: '本系统输出仅用于家庭健康监测与科普参考，不构成医疗诊断，不推荐具体处方药剂量。'
    }
  ];

  const STATUS_LABELS = {
    pending_confirm: '待确认',
    pending_remind: '待提醒',
    pending_call: '待沟通',
    done: '已完成'
  };

  let activeDraft = null;
  let editingTaskId = null;

  function app() {
    return window.HM_APP || null;
  }

  function isoOffset(daysAgo) {
    const d = new Date();
    d.setDate(d.getDate() - daysAgo);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  }

  // ---------- 1. 14 天异地慢病家庭示例数据预置 ----------
  function buildGuestDemoDataset() {
    const bpSeriesFather = [
      [13, 132, 84, 72, '晨起', '已服药', ''],
      [12, 130, 82, 70, '晨起', '已服药', ''],
      [11, 136, 86, 74, '晨起', '已服药', '昨晚吃得偏咸'],
      [10, 129, 81, 69, '晨起', '已服药', ''],
      [9, 131, 83, 71, '晨起', '已服药', ''],
      [8, 134, 84, 73, '晚间', '已服药', '散步30分钟后'],
      [7, 128, 80, 68, '晨起', '已服药', ''],
      [6, 133, 85, 72, '晨起', '已服药', ''],
      [5, 138, 87, 76, '晨起', '已服药', '降温未加衣'],
      [4, 131, 82, 71, '晨起', '已服药', ''],
      [3, 134, 84, 72, '晨起', '已服药', ''],
      [2, 142, 90, 78, '晨起', '未服药/漏服', '早起外出忘带氨氯地平'],
      [1, 146, 92, 80, '晨起', '已服药', '连续第2天偏高，略感头胀'],
      [0, 139, 88, 75, '晨起', '已服药', '已提醒低盐饮食并复测']
    ];

    const familyMembers = [
      {
        id: 'm_dad',
        relation: '爸爸',
        name: '林建国',
        age: 62,
        conditions: '原发性高血压（2级，居家监测）',
        medications: '苯磺酸氨氯地平片 5mg 每日晨起 1 片',
        emergencyName: '林同学（异地子女）',
        emergencyPhone: '138-0013-8000'
      },
      {
        id: 'm_mom',
        relation: '妈妈',
        name: '周梅',
        age: 59,
        conditions: '空腹血糖偏高（饮食控制中）',
        medications: '无处方药，定期监测空腹血糖',
        emergencyName: '林同学（异地子女）',
        emergencyPhone: '138-0013-8000'
      }
    ];

    const familyRecords = bpSeriesFather.map(function (row, idx) {
      const date = isoOffset(row[0]);
      const parts = [row[1] + '/' + row[2] + ' mmHg', '心率 ' + row[3], row[4], row[5]];
      if (row[6]) parts.push(row[6]);
      return {
        id: 'fr_dad_' + idx,
        memberId: 'm_dad',
        type: '血压',
        date: date,
        content: parts.join(' · ')
      };
    });
    familyRecords.push(
      { id: 'fr_mom_1', memberId: 'm_mom', type: '血糖', date: isoOffset(3), content: '空腹血糖 6.3 mmol/L · 晚餐米饭偏多' },
      { id: 'fr_mom_2', memberId: 'm_mom', type: '血糖', date: isoOffset(0), content: '空腹血糖 5.8 mmol/L · 粗细粮搭配后回落' }
    );

    const collabTasks = [
      {
        id: 'ct_demo_1',
        memberId: 'm_dad',
        memberName: '爸爸',
        title: '爸爸昨晨血压 146/92 mmHg（连续偏高），需电话核实服药与饮食盐量',
        category: '异常复核',
        assignee: '子女（林同学）',
        status: 'pending_confirm',
        triggerSource: 'auto_bp_alert',
        relatedMetric: '146/92 mmHg（近7次均值 137/86）',
        feedback: '',
        createdAt: isoOffset(1) + ' 08:20',
        updatedAt: isoOffset(1) + ' 08:20'
      },
      {
        id: 'ct_demo_2',
        memberId: 'm_dad',
        memberName: '爸爸',
        title: '本周五提醒爸爸携带 14 天家庭血压周报到社区卫生服务中心复诊',
        category: '复诊准备',
        assignee: '子女（林同学）',
        status: 'pending_remind',
        triggerSource: 'manual',
        relatedMetric: '血压连续记录 14/14 天',
        feedback: '已提前预约周五上午门诊号',
        createdAt: isoOffset(2) + ' 19:00',
        updatedAt: isoOffset(1) + ' 20:10'
      },
      {
        id: 'ct_demo_3',
        memberId: 'm_dad',
        memberName: '爸爸',
        title: '核对苯磺酸氨氯地平片剩余药量，防止月底断药',
        category: '用药提醒',
        assignee: '子女（林同学）',
        status: 'done',
        triggerSource: 'manual',
        relatedMetric: '氨氯地平 5mg',
        feedback: '已视频核对药盒，剩余 18 片，已帮忙在线续配一盒',
        createdAt: isoOffset(5) + ' 18:30',
        updatedAt: isoOffset(4) + ' 20:05'
      }
    ];

    const today = isoOffset(0);
    const weightHistory = [];
    for (let d = 13; d >= 0; d--) {
      weightHistory.push({
        date: isoOffset(d),
        weight: Number((62.4 - (13 - d) * 0.05).toFixed(1))
      });
    }

    const sleepLog = [];
    const hoursArr = [7.4, 7.1, 6.8, 7.6, 7.5, 6.9, 7.3];
    for (let s = 6; s >= 0; s--) {
      sleepLog.push({
        date: isoOffset(s),
        hours: hoursArr[6 - s],
        quality: hoursArr[6 - s] >= 7.2 ? '良好' : '一般',
        note: ''
      });
    }

    const sportHistory = {};
    for (let sp = 6; sp >= 0; sp--) {
      sportHistory[isoOffset(sp)] = {
        kcal: 280 + ((6 - sp) % 3) * 75,
        steps: 6800 + ((6 - sp) % 3) * 1100,
        minutes: 32 + ((6 - sp) % 3) * 10
      };
    }

    const mealLog = [
      { id: 'ml_1', date: today, meal: '早餐', text: '燕麦粥 1碗 · 水煮蛋 1个 · 无糖豆浆', kcal: 360, protein: 18, carb: 46, fat: 10, fiber: 6 },
      { id: 'ml_2', date: today, meal: '午餐', text: '清蒸鲈鱼 · 蒜蓉西兰花 · 杂粮饭半碗', kcal: 540, protein: 36, carb: 58, fat: 14, fiber: 8 },
      { id: 'ml_3', date: isoOffset(1), meal: '晚餐', text: '番茄鸡蛋面（少盐） · 凉拌黄瓜', kcal: 480, protein: 20, carb: 68, fat: 12, fiber: 5 }
    ];

    const reminders = [
      { id: 'rem_1', memberId: 'm_dad', title: '提醒爸爸明早起床后静坐5分钟复测晨起血压', date: today, done: false },
      { id: 'rem_2', memberId: 'm_mom', title: '周末核对妈妈空腹血糖并控制晚餐主食量', date: today, done: false }
    ];

    return {
      profile: {
        nickname: '林同学（异地子女演示）',
        name: '林同学',
        gender: '男',
        height: 174,
        weight: 61.8,
        age: 20
      },
      preferences: {
        goal: '保持健康',
        conditions: ['家人高血压监测'],
        taste: '清淡',
        dietType: '均衡饮食',
        meals: '3 餐',
        age: '20'
      },
      bp: { systolic: 118, diastolic: 76 },
      glucose: 5.1,
      vitalsHistory: {
        bp: [
          { date: isoOffset(6) + ' 08:10', text: '116/75' },
          { date: isoOffset(3) + ' 08:15', text: '120/78' },
          { date: today + ' 08:05', text: '118/76' }
        ],
        glucose: [
          { date: isoOffset(5) + ' 07:40', text: '5.0' },
          { date: today + ' 07:35', text: '5.1' }
        ],
        fat: [{ date: today + ' 08:00', text: '18.6' }]
      },
      weightHistory: weightHistory,
      sleepLog: sleepLog,
      mealLog: mealLog,
      sport: { goal: { kcal: 400, steps: 8000, minutes: 45 }, history: sportHistory },
      moodLog: (function () {
        const obj = {};
        obj[today] = { mood: '平静', note: '已给爸爸打电话核对晨起血压，状态稳定' };
        return obj;
      })(),
      familyMembers: familyMembers,
      familyRecords: familyRecords,
      collabTasks: collabTasks,
      reminders: reminders,
      dietActivity: 1.375
    };
  }

  function ensureGuestSeed(force) {
    const A = app();
    if (!A) return;
    const existingMembers = A.loadData('familyMembers', []);
    const existingTasks = A.loadData('collabTasks', []);
    if (!force && existingMembers && existingMembers.length > 0 && existingTasks && existingTasks.length > 0) {
      updateDemoBar();
      return;
    }
    const seed = buildGuestDemoDataset();
    if (force) A.clearCache();
    Object.keys(seed).forEach(function (k) {
      A.saveData(k, seed[k]);
    });
    updateDemoBar();
  }

  function updateDemoBar() {
    const bar = document.getElementById('guestDemoBar');
    const A = app();
    if (!bar || !A) return;
    bar.hidden = A.isServerMode();
  }

  // ---------- 2. 血压解析与写前安全校验（本地与后端一致） ----------
  function parseBpNumberPair(text) {
    const m = String(text || '').match(/(\d{2,3})\s*[/／]\s*(\d{2,3})/);
    if (!m) return null;
    return { systolic: Number(m[1]), diastolic: Number(m[2]) };
  }

  function parseBpTextLocal(text) {
    const raw = String(text || '').trim();
    if (!raw) return null;
    let sys = null;
    let dia = null;
    const slash = raw.match(/(\d{2,3})\s*[/／]\s*(\d{2,3})/);
    if (slash) {
      sys = Number(slash[1]);
      dia = Number(slash[2]);
    } else {
      const ms = raw.match(/(?:高压|收缩压)\s*(?:是|为|约)?\s*(\d{2,3})/);
      const md = raw.match(/(?:低压|舒张压)\s*(?:是|为|约)?\s*(\d{2,3})/);
      if (ms && md) {
        sys = Number(ms[1]);
        dia = Number(md[1]);
      }
    }
    if (sys === null || dia === null) return null;

    const mp = raw.match(/(?:心率|脉搏)\s*(?:是|为)?\s*(\d{2,3})/);
    const pulse = mp ? Number(mp[1]) : null;

    let period = '晨起';
    if (/晚上|晚间|睡前|今晚|昨晚/.test(raw)) period = '晚间';
    else if (/中午|下午|午后/.test(raw)) period = '午后';

    let medStatus = '未说明';
    if (/忘吃|没吃药|漏服|未服药|忘了吃/.test(raw)) medStatus = '未服药/漏服';
    else if (/吃了药|已服药|吃了降压药|氨氯地平|缬沙坦|硝苯地平|服了/.test(raw)) medStatus = '已服药';

    let member = '本人';
    if (/爸爸|父亲|老爸|我爸/.test(raw)) member = '爸爸';
    else if (/妈妈|母亲|老妈|我妈/.test(raw)) member = '妈妈';
    else if (/爷爷/.test(raw)) member = '爷爷';
    else if (/奶奶/.test(raw)) member = '奶奶';

    const symMatches = raw.match(/头晕|头痛|胸闷|心慌|乏力|视物模糊|头胀/g);
    const symptom = symMatches ? Array.from(new Set(symMatches)).join('、') : '';

    return {
      systolic: sys,
      diastolic: dia,
      pulse: pulse,
      measuredPeriod: period,
      medStatus: medStatus,
      member: member,
      symptom: symptom
    };
  }

  function getRecentBpPairs(memberIdOrName) {
    const A = app();
    if (!A) return [];
    const members = A.loadData('familyMembers', []) || [];
    const records = A.loadData('familyRecords', []) || [];
    let member = members.find(function (m) {
      return m.id === memberIdOrName || m.relation === memberIdOrName || m.name === memberIdOrName;
    });
    if (member) {
      return records
        .filter(function (r) { return r.memberId === member.id && r.type === '血压'; })
        .sort(function (a, b) { return String(a.date).localeCompare(String(b.date)); })
        .map(function (r) {
          const pair = parseBpNumberPair(r.content);
          return pair ? Object.assign({ date: r.date, content: r.content }, pair) : null;
        })
        .filter(Boolean);
    }
    const vh = (A.loadData('vitalsHistory', {}) || {}).bp || [];
    return vh.map(function (r) {
      const pair = parseBpNumberPair(r.text);
      return pair ? Object.assign({ date: String(r.date || '').slice(0, 10), content: r.text }, pair) : null;
    }).filter(Boolean);
  }

  function validateBpLocal(sys, dia, pulse, recentPairs, imageQuality, confidence) {
    const errors = [];
    const warnings = [];
    let requiresDoubleConfirm = false;

    const s = Number(sys);
    const d = Number(dia);
    const p = (pulse === '' || pulse === null || pulse === undefined) ? null : Number(pulse);

    if (!isFinite(s) || !isFinite(d) || !sys || !dia) {
      errors.append ? null : errors.push('请输入完整的收缩压（高压）和舒张压（低压）数值');
    } else {
      if (s < 60 || s > 260) errors.push('收缩压 ' + s + ' 超出合理生理范围（60–260 mmHg）');
      if (d < 30 || d > 160) errors.push('舒张压 ' + d + ' 超出合理生理范围（30–160 mmHg）');
      if (s <= d) errors.push('收缩压（' + s + '）必须大于舒张压（' + d + '），疑似高低压颠倒');
      else if (s - d < 15) {
        warnings.push('脉压差过小（' + (s - d) + ' mmHg），请确认读数无误');
        requiresDoubleConfirm = true;
      }
    }
    if (p !== null && isFinite(p) && (p < 35 || p > 200)) {
      errors.push('心率 ' + p + ' 超出合理范围（35–200 次/分）');
    }
    if (errors.length) {
      return {
        valid: false, blocked: true, abnormal: false, urgent: false,
        level: '非法数值（已拦截）', requiresDoubleConfirm: true,
        shouldCreateCollabTask: false, errors: errors, warnings: warnings, baseline: null
      };
    }

    let level = '正常（<120/80）';
    let abnormal = false;
    let urgent = false;
    if (s >= 180 || d >= 110) {
      level = '急症警戒（≥180/110）';
      abnormal = true;
      urgent = true;
      warnings.push('已达 ≥180/110 mmHg 急症红线，如伴头痛、胸闷、视物模糊请立即就医！');
      requiresDoubleConfirm = true;
    } else if (s >= 140 || d >= 90) {
      level = '高血压范围（≥140/90）';
      abnormal = true;
      warnings.push('读数达到高血压范围（≥140/90），保存后将自动为异地子女生成异常复核协同任务。');
    } else if (s >= 135 || d >= 85) {
      level = '家庭自测偏高（≥135/85）';
      abnormal = true;
      warnings.push('达到家庭自测偏高阈值（≥135/85，参照 2024 高血压指南），建议复测并核对服药。');
    } else if (s < 90 || d < 60) {
      level = '血压偏低（<90/60）';
      abnormal = true;
      warnings.push('血压偏低，若伴头晕乏力请及时联系家人或就医。');
    } else if (s >= 120 || d >= 80) {
      level = '正常高值（120-139/80-89）';
    }

    if (imageQuality && /重拍|模糊|反光|倾斜/.test(imageQuality)) {
      warnings.push('拍摄质量门控提示「' + imageQuality + '」，请人工核对屏幕数字后再确认写入。');
      requiresDoubleConfirm = true;
    }
    if (typeof confidence === 'number' && confidence < 0.75) {
      warnings.push('模型识别置信度偏低（' + Math.round(confidence * 100) + '%），已禁止静默入库，请二次核对。');
      requiresDoubleConfirm = true;
    }

    const last7 = (recentPairs || []).slice(-7);
    let baseline = null;
    if (last7.length) {
      const meanS = last7.reduce(function (acc, x) { return acc + x.systolic; }, 0) / last7.length;
      const meanD = last7.reduce(function (acc, x) { return acc + x.diastolic; }, 0) / last7.length;
      const deltaS = Math.round(s - meanS);
      const deltaD = Math.round(d - meanD);
      const dev = Math.abs(deltaS) >= 25 || Math.abs(deltaD) >= 15;
      baseline = {
        count: last7.length,
        meanSystolic: Math.round(meanS),
        meanDiastolic: Math.round(meanD),
        deltaSystolic: deltaS,
        deltaDiastolic: deltaD,
        deviationAlert: dev
      };
      if (dev) {
        requiresDoubleConfirm = true;
        warnings.push('历史基线突变预警：较近 ' + last7.length + ' 次均值（' + Math.round(meanS) + '/' + Math.round(meanD) +
          '）变化 ' + (deltaS >= 0 ? '+' : '') + deltaS + '/' + (deltaD >= 0 ? '+' : '') + deltaD + ' mmHg，请二次确认是否误读或漏服药！');
      }
    }

    return {
      valid: true,
      blocked: false,
      abnormal: abnormal,
      urgent: urgent,
      level: level,
      requiresDoubleConfirm: requiresDoubleConfirm,
      shouldCreateCollabTask: abnormal || (baseline && baseline.deviationAlert),
      errors: [],
      warnings: warnings,
      baseline: baseline
    };
  }

  // ---------- 3. 本地权威指南检索 + 动态可溯源 AI 回复 ----------
  function matchGuidelinesLocal(query) {
    const q = String(query || '').toLowerCase();
    const scored = LOCAL_GUIDELINES.map(function (g) {
      let score = 0;
      g.keywords.forEach(function (kw) {
        if (q.indexOf(kw.toLowerCase()) !== -1) score += 5;
      });
      return { g: g, score: score };
    }).filter(function (x) { return x.score > 0; })
      .sort(function (a, b) { return b.score - a.score; });

    const out = scored.slice(0, 3).map(function (x) { return x.g; });
    if (/180|110|胸痛|头晕|急诊/.test(q) && !out.some(function (x) { return x.id === 'G-HTN-04'; })) {
      out.push(LOCAL_GUIDELINES[3]);
    }
    if (!out.length) out.push(LOCAL_GUIDELINES[0], LOCAL_GUIDELINES[4]);
    return out.slice(0, 3);
  }

  function buildLocalRecordRefs() {
    const A = app();
    if (!A) return [];
    const refs = [];
    const members = A.loadData('familyMembers', []) || [];
    const records = (A.loadData('familyRecords', []) || []).slice().sort(function (a, b) {
      return String(b.date).localeCompare(String(a.date));
    });
    records.slice(0, 2).forEach(function (r, idx) {
      const m = members.find(function (x) { return x.id === r.memberId; });
      refs.push({
        refId: 'R-FAM-' + (idx + 1),
        date: r.date,
        label: (m ? m.relation : '家人') + ' · ' + r.type + '：' + String(r.content || '').slice(0, 28)
      });
    });
    const bp = A.loadData('bp', null);
    if (bp && bp.systolic && bp.diastolic) {
      refs.push({ refId: 'R-BP-SELF', date: isoOffset(0), label: '本人最新血压：' + bp.systolic + '/' + bp.diastolic + ' mmHg' });
    }
    return refs;
  }

  function buildLocalReply(text) {
    const A = app();
    const q = String(text || '').trim();
    const lower = q.toLowerCase();
    const isQuestion = /吗|？|\?|能不能|怎么办|注意|建议|为什么|多少/.test(q);

    // 1. 识别口语血压录入 -> 弹出校验草稿卡（绝不静默写库）
    const parsedBp = parseBpTextLocal(q);
    if (parsedBp && (!isQuestion || /记|帮我|刚测|测了|录入/.test(q))) {
      const recent = getRecentBpPairs(parsedBp.member);
      const val = validateBpLocal(parsedBp.systolic, parsedBp.diastolic, parsedBp.pulse, recent);
      const guides = matchGuidelinesLocal(q + ' 血压');
      const replyLines = [
        '已从你的描述中解析出【' + parsedBp.member + '】的血压草稿：' + parsedBp.systolic + '/' + parsedBp.diastolic + ' mmHg（' + parsedBp.measuredPeriod + ' · ' + parsedBp.medStatus + '）。',
        '写前校验分级：' + val.level + (val.warnings.length ? '。注意：' + val.warnings[0] : '，符合近期历史基线。'),
        '为防止误识别污染健康档案，我已为你打开可编辑草稿确认卡，支持语音播报核对后再写入。'
      ];
      return {
        reply: replyLines.join('\n'),
        citations: {
          records: buildLocalRecordRefs(),
          guidelines: guides,
          safetyNotice: '本建议仅用于家庭健康监测与科普参考，不构成医疗诊断。'
        },
        action: Object.assign({ type: 'bp_record', validation: val }, parsedBp)
      };
    }

    const guides = matchGuidelinesLocal(q);
    const refs = buildLocalRecordRefs();
    const safety = '当前为本地可溯源规则模式（登录后启用在线大模型）。内容仅供健康科普，不构成医疗诊断。';

    if (/怎么用|教程|不会用/.test(lower)) {
      return {
        reply: '快速上手指南：\n1）首页顶部可一键切换「长辈极简录入（大字版）」，支持拍血压计、一句话语音记血压与语音播报核对。\n2）首页「异地家庭慢病协同看板」可查看爸爸近 14 天血压曲线、异常自动触发的待办任务，并一键生成微信家庭周报。\n3）直接在这里说「爸爸早上测血压 152/94，忘吃降压药」，系统会自动弹出带历史基线校验的确认草稿卡。',
        citations: { records: refs.slice(0, 1), guidelines: [LOCAL_GUIDELINES[1]], safetyNotice: safety },
        action: null
      };
    }

    if (/饮食|营养|蛋白|热量|吃什么|控盐/.test(lower)) {
      const targets = (A && typeof A.getNutritionTargets === 'function') ? A.getNutritionTargets() : { kcal: 0, protein: 0 };
      const mealLog = (A ? A.loadData('mealLog', []) : []) || [];
      const todayMeals = mealLog.filter(function (m) { return m.date === isoOffset(0); });
      const todayKcal = Math.round(todayMeals.reduce(function (s, m) { return s + (Number(m.kcal) || 0); }, 0));
      const todayPro = Math.round(todayMeals.reduce(function (s, m) { return s + (Number(m.protein) || 0); }, 0));
      const targetStr = targets.kcal > 0
        ? ('你今日已记录 ' + todayKcal + ' / ' + Math.round(targets.kcal) + ' kcal，蛋白质 ' + todayPro + ' / ' + Math.round(targets.protein) + ' g。')
        : '完善身高体重后可生成个性化每日营养配额。';
      return {
        reply: '基于你当前真实档案的饮食建议：\n1）' + targetStr + '\n2）高血压家庭日常重在“限盐增蔬”：参照 [' + guides[0].id + '] ' + guides[0].summary + '\n3）如需拍照估热量，上传餐食图后可在写入前逐项修改菜品热量或删除误识别项。',
        citations: { records: refs, guidelines: guides, safetyNotice: safety },
        action: null
      };
    }

    if (/运动|跑步|步数|锻炼/.test(lower)) {
      const sport = (A ? A.loadData('sport', null) : null) || { goal: { kcal: 400, steps: 8000, minutes: 45 }, history: {} };
      const todayRec = (sport.history || {})[isoOffset(0)] || { kcal: 0, steps: 0, minutes: 0 };
      const goalKcal = (sport.goal && sport.goal.kcal) || 400;
      const pct = Math.min(100, Math.round((todayRec.kcal / goalKcal) * 100));
      return {
        reply: '基于你今日真实运动记录的建议：\n1）今日已累计运动 ' + todayRec.minutes + ' 分钟、约 ' + todayRec.kcal + ' kcal（完成今日目标的 ' + pct + '%），步数 ' + todayRec.steps + ' 步。\n2）参照 [' + guides[0].id + '] ' + guides[0].summary,
        citations: { records: refs, guidelines: guides, safetyNotice: safety },
        action: null
      };
    }

    // 默认聚焦异地慢病血压与家庭档案回答
    const dadPairs = getRecentBpPairs('m_dad');
    const lastDad = dadPairs.length ? dadPairs[dadPairs.length - 1] : null;
    const meanDad = dadPairs.length
      ? Math.round(dadPairs.slice(-7).reduce(function (a, b) { return a + b.systolic; }, 0) / Math.min(7, dadPairs.length)) + '/' +
        Math.round(dadPairs.slice(-7).reduce(function (a, b) { return a + b.diastolic; }, 0) / Math.min(7, dadPairs.length))
      : null;

    const lines = [];
    if (lastDad) {
      lines.push('1）结合档案中【爸爸】的真实记录：最近一次血压 ' + lastDad.systolic + '/' + lastDad.diastolic + ' mmHg（' + lastDad.date + '），近 7 次均值 ' + meanDad + ' mmHg。');
    } else {
      lines.push('1）当前尚未查到近期家庭血压记录，建议点击顶部「长辈极简录入」或「拍照/快速记血压」先记录一次。');
    }
    lines.push('2）依据 [' + guides[0].id + '] ' + guides[0].source + '：' + guides[0].summary);
    if (guides[1]) {
      lines.push('3）补充要点 [' + guides[1].id + ']：' + guides[1].summary);
    }
    lines.push('4）异地协同建议：若连续 2 天晨起 ≥140/90 mmHg，建议通过首屏协同看板联系核实是否漏服降压药，并导出 14 天周报供复诊参考。');

    return {
      reply: lines.join('\n'),
      citations: { records: refs, guidelines: guides, safetyNotice: safety },
      action: null
    };
  }

  // ---------- 4. 异地家庭慢病协同看板渲染 ----------
  function renderBpSvgChart(pairs) {
    const wrap = document.getElementById('chronicBpChart');
    if (!wrap) return;
    if (!pairs.length) {
      wrap.innerHTML = '<div style="padding:36px 12px;text-align:center;color:#7a7468;font-size:13px;">该成员暂无血压记录，点击右上角「+ 拍照/快速记血压」录入第一条</div>';
      return;
    }
    const list = pairs.slice(-14);
    const w = 520;
    const h = 152;
    const padL = 34;
    const padR = 14;
    const padT = 16;
    const padB = 24;
    const minY = 60;
    const maxY = Math.max(165, Math.max.apply(null, list.map(function (x) { return x.systolic; })) + 10);

    function xPos(i) {
      if (list.length === 1) return padL + (w - padL - padR) / 2;
      return padL + (i / (list.length - 1)) * (w - padL - padR);
    }
    function yPos(v) {
      const clamped = Math.max(minY, Math.min(maxY, v));
      return padT + ((maxY - clamped) / (maxY - minY)) * (h - padT - padB);
    }

    const sysPts = list.map(function (p, i) { return xPos(i).toFixed(1) + ',' + yPos(p.systolic).toFixed(1); }).join(' ');
    const diaPts = list.map(function (p, i) { return xPos(i).toFixed(1) + ',' + yPos(p.diastolic).toFixed(1); }).join(' ');
    const refSysY = yPos(135).toFixed(1);
    const refDiaY = yPos(85).toFixed(1);

    let dots = '';
    let labels = '';
    list.forEach(function (p, i) {
      const x = xPos(i);
      const ys = yPos(p.systolic);
      const yd = yPos(p.diastolic);
      const alert = p.systolic >= 135 || p.diastolic >= 85;
      dots += '<circle cx="' + x.toFixed(1) + '" cy="' + ys.toFixed(1) + '" r="' + (alert ? 4.2 : 3.2) +
        '" fill="' + (alert ? '#c25843' : '#d98c5f') + '"><title>' + p.date + ' ' + p.systolic + '/' + p.diastolic + '</title></circle>';
      dots += '<circle cx="' + x.toFixed(1) + '" cy="' + yd.toFixed(1) + '" r="3" fill="#4a7c59"><title>' + p.date + ' 低压 ' + p.diastolic + '</title></circle>';
      if (i === 0 || i === list.length - 1 || i % Math.max(1, Math.floor(list.length / 4)) === 0) {
        labels += '<text x="' + x.toFixed(1) + '" y="' + (h - 6) + '" text-anchor="middle" font-size="10" fill="#7a7468">' +
          String(p.date || '').slice(5) + '</text>';
      }
    });

    wrap.innerHTML =
      '<svg viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none" aria-label="家庭血压趋势图">' +
        '<line x1="' + padL + '" y1="' + refSysY + '" x2="' + (w - padR) + '" y2="' + refSysY + '" stroke="#d98c5f" stroke-dasharray="4 4" stroke-width="1.2"/>' +
        '<text x="4" y="' + (Number(refSysY) + 3) + '" font-size="10" fill="#b86b3a">135</text>' +
        '<line x1="' + padL + '" y1="' + refDiaY + '" x2="' + (w - padR) + '" y2="' + refDiaY + '" stroke="#8fb08a" stroke-dasharray="3 4" stroke-width="1"/>' +
        '<text x="8" y="' + (Number(refDiaY) + 3) + '" font-size="10" fill="#4a7c59">85</text>' +
        '<polyline fill="none" stroke="#c25843" stroke-width="2.2" points="' + sysPts + '"/>' +
        '<polyline fill="none" stroke="#4a7c59" stroke-width="2" points="' + diaPts + '"/>' +
        dots + labels +
      '</svg>';
  }

  function renderCollabDashboard() {
    const A = app();
    if (!A) return;
    const select = document.getElementById('chronicMemberSelect');
    const metaEl = document.getElementById('chronicMemberMeta');
    const taskListEl = document.getElementById('collabTaskList');
    const badgeEl = document.getElementById('collabPendingCount');
    if (!select || !taskListEl) return;

    const members = A.loadData('familyMembers', []) || [];
    const prevVal = select.value;
    select.innerHTML = '';
    members.forEach(function (m) {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = (m.relation || '家人') + (m.name ? '（' + m.name + '）' : '');
      select.appendChild(opt);
    });
    const selfOpt = document.createElement('option');
    selfOpt.value = '__self__';
    selfOpt.textContent = '本人档案';
    select.appendChild(selfOpt);

    if (prevVal && Array.from(select.options).some(function (o) { return o.value === prevVal; })) {
      select.value = prevVal;
    } else if (members.length) {
      select.value = members[0].id;
    }

    const selectedId = select.value;
    const member = members.find(function (m) { return m.id === selectedId; });
    if (member) {
      metaEl.textContent = '正在关注：' + member.relation +
        (member.age ? ' · ' + member.age + ' 岁' : '') +
        (member.conditions ? ' · ' + member.conditions : '') +
        (member.medications ? ' · 用药：' + member.medications : '');
    } else {
      metaEl.textContent = '正在关注：本人慢病与核心体征档案（可在「家人健康」添加父母档案进行异地协同）';
    }

    const pairs = getRecentBpPairs(selectedId === '__self__' ? '本人' : selectedId);
    renderBpSvgChart(pairs);

    const last7 = pairs.slice(-7);
    const meanEl = document.getElementById('ckpiMeanBp');
    const passEl = document.getElementById('ckpiPassRate');
    const adhEl = document.getElementById('ckpiAdherence');
    if (last7.length) {
      const ms = Math.round(last7.reduce(function (a, x) { return a + x.systolic; }, 0) / last7.length);
      const md = Math.round(last7.reduce(function (a, x) { return a + x.diastolic; }, 0) / last7.length);
      const okCount = last7.filter(function (x) { return x.systolic < 135 && x.diastolic < 85; }).length;
      meanEl.textContent = ms + '/' + md + ' mmHg';
      passEl.textContent = Math.round((okCount / last7.length) * 100) + '%（' + okCount + '/' + last7.length + '）';
      const uniqDays = new Set(pairs.slice(-14).map(function (x) { return x.date; })).size;
      adhEl.textContent = Math.min(14, uniqDays) + '/14 天';
    } else {
      meanEl.textContent = '—';
      passEl.textContent = '—';
      adhEl.textContent = '0/14 天';
    }

    // 渲染协同任务
    const tasks = (A.loadData('collabTasks', []) || []).slice();
    const pending = tasks.filter(function (t) { return t.status !== 'done'; }).length;
    badgeEl.textContent = pending + ' 待处理';

    if (!tasks.length) {
      taskListEl.innerHTML = '<div style="padding:18px 8px;text-align:center;color:#7a7468;font-size:12.5px;">暂无待处理的异地协同任务；当家人录入偏高血压时会自动生成。</div>';
      return;
    }

    taskListEl.innerHTML = tasks.map(function (t) {
      const stLabel = STATUS_LABELS[t.status] || t.status;
      const isDone = t.status === 'done';
      return '<div class="ctask-item' + (isDone ? ' is-done' : '') + '">' +
        '<div class="ctask-top">' +
          '<span class="ctask-status st-' + A.escapeHtml(t.status) + '">' + A.escapeHtml(stLabel) + '</span>' +
          '<span style="font-size:11px;color:#7a7468;">' + A.escapeHtml(t.category || '协同') + ' · ' +
          (t.triggerSource === 'auto_bp_alert' ? '⚡血压异常自动触发' : '手动创建') + '</span>' +
        '</div>' +
        '<div class="ctask-title">' + A.escapeHtml(t.title) + '</div>' +
        '<div class="ctask-meta"><span>负责人：' + A.escapeHtml(t.assignee || '子女') +
          (t.relatedMetric ? ' · ' + A.escapeHtml(t.relatedMetric) : '') + '</span></div>' +
        (t.feedback ? '<div class="ctask-fb">处理反馈：' + A.escapeHtml(t.feedback) + '</div>' : '') +
        '<div class="ctask-actions">' +
          '<button type="button" class="' + (isDone ? '' : 'primary-mini') + '" data-edit-task="' + A.escapeHtml(t.id) + '">' +
            (isDone ? '查看/修改反馈' : '流转状态 / 登记反馈') +
          '</button>' +
          (!isDone ? '<button type="button" data-done-task="' + A.escapeHtml(t.id) + '">快捷标为已完成</button>' : '') +
        '</div>' +
      '</div>';
    }).join('');

    taskListEl.querySelectorAll('[data-edit-task]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        openCollabTaskModal(btn.dataset.editTask);
      });
    });
    taskListEl.querySelectorAll('[data-done-task]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        quickCompleteTask(btn.dataset.doneTask);
      });
    });
  }

  function quickCompleteTask(taskId) {
    const A = app();
    if (!A) return;
    const tasks = (A.loadData('collabTasks', []) || []).slice();
    const item = tasks.find(function (t) { return t.id === taskId; });
    if (!item) return;
    item.status = 'done';
    if (!item.feedback) item.feedback = '已通过电话与家人确认并完成提醒';
    item.updatedAt = isoOffset(0);
    A.saveData('collabTasks', tasks);
    renderCollabDashboard();
    A.showToast('协同任务已标记完成');
  }

  // ---------- 5. 血压草稿校验弹窗 + 语音回放确认 ----------
  function populateMemberSelect(selectEl, preferred) {
    const A = app();
    if (!selectEl || !A) return;
    const members = A.loadData('familyMembers', []) || [];
    selectEl.innerHTML = '';
    members.forEach(function (m) {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = m.relation + (m.name ? '（' + m.name + '）' : '');
      selectEl.appendChild(opt);
    });
    const selfOpt = document.createElement('option');
    selfOpt.value = '__self__';
    selfOpt.textContent = '本人';
    selectEl.appendChild(selfOpt);

    if (preferred) {
      const hit = members.find(function (m) {
        return m.id === preferred || m.relation === preferred || m.name === preferred;
      });
      if (hit) selectEl.value = hit.id;
      else if (preferred === '本人' || preferred === '__self__') selectEl.value = '__self__';
    }
  }

  function runLiveDraftValidation() {
    const box = document.getElementById('bpValidationBox');
    const textEl = document.getElementById('bpValidationText');
    const dblRow = document.getElementById('bpDoubleConfirmRow');
    const dblCheck = document.getElementById('bpDoubleConfirmCheck');
    const saveBtn = document.getElementById('bpDraftSave');
    if (!box || !textEl) return null;

    const memberVal = document.getElementById('bpDraftMember').value;
    const sys = document.getElementById('bpDraftSys').value;
    const dia = document.getElementById('bpDraftDia').value;
    const pulse = document.getElementById('bpDraftPulse').value;
    const recent = getRecentBpPairs(memberVal === '__self__' ? '本人' : memberVal);
    const iq = activeDraft ? activeDraft.imageQuality : null;
    const conf = activeDraft ? activeDraft.confidence : null;

    const result = validateBpLocal(sys, dia, pulse, recent, iq, conf);
    if (activeDraft) activeDraft.validation = result;

    if (result.blocked) {
      box.className = 'bp-validation-box err';
      textEl.textContent = '✕ 写前校验拦截：' + result.errors.join('；');
      dblRow.hidden = true;
      saveBtn.disabled = true;
      return result;
    }

    saveBtn.disabled = false;
    if (result.requiresDoubleConfirm || result.warnings.length) {
      box.className = 'bp-validation-box warn';
      textEl.textContent = '⚠ ' + result.level + '：' + result.warnings.join(' ');
      dblRow.hidden = !result.requiresDoubleConfirm;
      if (!result.requiresDoubleConfirm) dblCheck.checked = true;
    } else {
      box.className = 'bp-validation-box ok';
      const baseTip = result.baseline
        ? '（近 ' + result.baseline.count + ' 次均值 ' + result.baseline.meanSystolic + '/' + result.baseline.meanDiastolic + '，波动平稳）'
        : '';
      textEl.textContent = '✓ 写前校验通过：' + result.level + baseTip + '。点击下方可语音播报核对后保存。';
      dblRow.hidden = true;
    }
    return result;
  }

  function openBpDraft(draft) {
    const A = app();
    if (!A) return;
    activeDraft = Object.assign({
      source: '快速录入',
      member: document.getElementById('chronicMemberSelect') ? document.getElementById('chronicMemberSelect').value : 'm_dad',
      systolic: '',
      diastolic: '',
      pulse: '',
      measuredPeriod: '晨起',
      medStatus: '已服药',
      symptom: '',
      imageQuality: '清晰',
      confidence: 1.0
    }, draft || {});

    populateMemberSelect(document.getElementById('bpDraftMember'), activeDraft.member);
    document.getElementById('bpDraftSourceTag').textContent = '录入来源：' + activeDraft.source;
    document.getElementById('bpDraftSys').value = activeDraft.systolic || '';
    document.getElementById('bpDraftDia').value = activeDraft.diastolic || '';
    document.getElementById('bpDraftPulse').value = activeDraft.pulse || '';
    document.getElementById('bpDraftPeriod').value = activeDraft.measuredPeriod || '晨起';
    document.getElementById('bpDraftMed').value = activeDraft.medStatus || '已服药';
    document.getElementById('bpDraftNote').value = activeDraft.symptom || activeDraft.note || '';
    document.getElementById('bpDoubleConfirmCheck').checked = false;

    runLiveDraftValidation();
    A.openMask(document.getElementById('bpDraftMask'));
  }

  function speakBpDraft() {
    const A = app();
    const memberSel = document.getElementById('bpDraftMember');
    const who = memberSel.options[memberSel.selectedIndex] ? memberSel.options[memberSel.selectedIndex].textContent : '本人';
    const sys = document.getElementById('bpDraftSys').value;
    const dia = document.getElementById('bpDraftDia').value;
    const period = document.getElementById('bpDraftPeriod').value;
    const med = document.getElementById('bpDraftMed').value;
    const sentence = '请核对待保存记录：' + who + '，' + period + '血压，高压 ' + (sys || '未填') +
      '，低压 ' + (dia || '未填') + '，服药状态为' + med + '。确认无误请点击保存。';

    if ('speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
        const utter = new SpeechSynthesisUtterance(sentence);
        utter.lang = 'zh-CN';
        utter.rate = 0.92;
        window.speechSynthesis.speak(utter);
        if (A) A.showToast('正在语音播报核对内容…');
        return;
      } catch (e) {}
    }
    if (A) A.showToast('播报预览：' + sentence);
  }

  function saveBpDraft() {
    const A = app();
    if (!A) return;
    const val = runLiveDraftValidation();
    if (!val || val.blocked) {
      A.showToast('数值校验未通过，已拦截写入');
      return;
    }
    if (val.requiresDoubleConfirm && !document.getElementById('bpDoubleConfirmCheck').checked) {
      A.showToast('触发基线波动或质量预警，请先勾选“已人工核对数值无误”');
      return;
    }

    const memberVal = document.getElementById('bpDraftMember').value;
    const sys = Math.round(Number(document.getElementById('bpDraftSys').value));
    const dia = Math.round(Number(document.getElementById('bpDraftDia').value));
    const pulse = document.getElementById('bpDraftPulse').value.trim();
    const period = document.getElementById('bpDraftPeriod').value;
    const med = document.getElementById('bpDraftMed').value;
    const note = document.getElementById('bpDraftNote').value.trim();
    const today = isoOffset(0);

    const members = A.loadData('familyMembers', []) || [];
    const member = members.find(function (m) { return m.id === memberVal; });

    if (member) {
      const records = (A.loadData('familyRecords', []) || []).slice();
      const parts = [sys + '/' + dia + ' mmHg'];
      if (pulse) parts.push('心率 ' + pulse);
      parts.push(period, med);
      if (note) parts.push(note);
      records.push({
        id: 'fr_' + Date.now(),
        memberId: member.id,
        type: '血压',
        date: today,
        content: parts.join(' · ')
      });
      A.saveData('familyRecords', records);

      // 异常血压或基线突变 -> 自动生成异地子女协同待办任务
      if (val.shouldCreateCollabTask) {
        const tasks = (A.loadData('collabTasks', []) || []).slice();
        tasks.unshift({
          id: 'ct_' + Date.now(),
          memberId: member.id,
          memberName: member.relation,
          title: member.relation + period + '血压 ' + sys + '/' + dia + ' mmHg（' + val.level + '），请尽快核实服药与复测',
          category: '异常复核',
          assignee: '子女（林同学）',
          status: 'pending_confirm',
          triggerSource: 'auto_bp_alert',
          relatedMetric: sys + '/' + dia + ' mmHg · ' + med,
          feedback: '',
          createdAt: today,
          updatedAt: today
        });
        A.saveData('collabTasks', tasks);
        A.showToast('已写入档案，并自动触发 1 条异地协同复核任务！');
      } else {
        A.showToast('已安全写入' + member.relation + '的血压档案');
      }
    } else {
      A.saveData('bp', { systolic: sys, diastolic: dia });
      const vh = A.loadData('vitalsHistory', {}) || {};
      if (!Array.isArray(vh.bp)) vh.bp = [];
      vh.bp.push({ date: today + ' ' + new Date().toTimeString().slice(0, 5), text: sys + '/' + dia });
      A.saveData('vitalsHistory', vh);
      A.showToast('已更新本人血压为 ' + sys + '/' + dia + ' mmHg');
    }

    A.closeMask(document.getElementById('bpDraftMask'));
    A.refreshAllViews();
  }

  // ---------- 6. 血压计拍照上传 / 一键演示 ----------
  async function handleBpMeterUpload(file) {
    const A = app();
    if (!A || !file) return;
    if (!A.isServerMode()) {
      A.showToast('离线演示模式：已模拟多模态血压计识别，请核对草稿');
      openBpDraft({
        source: '血压计拍照识别（本地演示）',
        member: 'm_dad',
        systolic: 148,
        diastolic: 92,
        pulse: 78,
        measuredPeriod: '晨起',
        medStatus: '已服药',
        imageQuality: '清晰',
        confidence: 0.93
      });
      return;
    }
    try {
      A.showToast('正在上传并识别血压计屏幕…');
      const url = await A.uploadImage(file);
      const res = await A.api('/api/ai/vision', {
        method: 'POST',
        body: { task: 'bp_meter', imageUrl: url, member: '爸爸' }
      });
      if (!res.ok) {
        A.showToast((res.data && res.data.error) || '识别失败，可手动核对录入');
        openBpDraft({ source: '拍照降级手工核对', member: 'm_dad' });
        return;
      }
      const r = res.data.result || {};
      openBpDraft({
        source: '多模态血压计识别（' + (res.data.model || 'VLM') + '）',
        member: 'm_dad',
        systolic: r.systolic || '',
        diastolic: r.diastolic || '',
        pulse: r.pulse || '',
        measuredPeriod: r.measuredPeriod || '晨起',
        imageQuality: r.imageQuality || '清晰',
        confidence: typeof r.confidence === 'number' ? r.confidence : 0.9,
        note: r.note || ''
      });
    } catch (err) {
      A.showToast('上传失败：' + err.message);
    }
  }

  // ---------- 7. 协同任务弹窗 & 异地家庭周报 ----------
  function openCollabTaskModal(taskId) {
    const A = app();
    if (!A) return;
    editingTaskId = taskId || null;
    populateMemberSelect(document.getElementById('collabMember'), 'm_dad');
    const tasks = A.loadData('collabTasks', []) || [];
    const existing = taskId ? tasks.find(function (t) { return t.id === taskId; }) : null;

    document.getElementById('collabModalTitle').textContent = existing ? '流转协同状态 / 登记处理反馈' : '新建异地家庭协同任务';
    document.getElementById('collabTitle').value = existing ? existing.title : '';
    document.getElementById('collabCategory').value = existing ? (existing.category || '异常复核') : '异常复核';
    document.getElementById('collabStatus').value = existing ? (existing.status || 'pending_confirm') : 'pending_confirm';
    document.getElementById('collabAssignee').value = existing ? (existing.assignee || '子女（林同学）') : '子女（林同学）';
    document.getElementById('collabFeedback').value = existing ? (existing.feedback || '') : '';
    if (existing && existing.memberId) {
      document.getElementById('collabMember').value = existing.memberId;
    }
    A.openMask(document.getElementById('collabTaskMask'));
  }

  function saveCollabTaskModal() {
    const A = app();
    if (!A) return;
    const title = document.getElementById('collabTitle').value.trim();
    if (!title) {
      A.showToast('请填写协同事项标题');
      return;
    }
    const memberSel = document.getElementById('collabMember');
    const memberId = memberSel.value === '__self__' ? null : memberSel.value;
    const memberName = memberSel.options[memberSel.selectedIndex] ? memberSel.options[memberSel.selectedIndex].textContent : '';
    const tasks = (A.loadData('collabTasks', []) || []).slice();
    const today = isoOffset(0);

    if (editingTaskId) {
      const idx = tasks.findIndex(function (t) { return t.id === editingTaskId; });
      if (idx !== -1) {
        tasks[idx] = Object.assign({}, tasks[idx], {
          memberId: memberId,
          memberName: memberName,
          title: title,
          category: document.getElementById('collabCategory').value,
          status: document.getElementById('collabStatus').value,
          assignee: document.getElementById('collabAssignee').value.trim() || '子女',
          feedback: document.getElementById('collabFeedback').value.trim(),
          updatedAt: today
        });
      }
    } else {
      tasks.unshift({
        id: 'ct_' + Date.now(),
        memberId: memberId,
        memberName: memberName,
        title: title,
        category: document.getElementById('collabCategory').value,
        assignee: document.getElementById('collabAssignee').value.trim() || '子女',
        status: document.getElementById('collabStatus').value,
        triggerSource: 'manual',
        relatedMetric: '',
        feedback: document.getElementById('collabFeedback').value.trim(),
        createdAt: today,
        updatedAt: today
      });
    }
    A.saveData('collabTasks', tasks);
    A.closeMask(document.getElementById('collabTaskMask'));
    renderCollabDashboard();
    A.showToast('协同任务已保存');
  }

  function openWeeklyReportModal() {
    const A = app();
    if (!A) return;
    const sel = document.getElementById('chronicMemberSelect');
    const selectedId = sel ? sel.value : 'm_dad';
    const members = A.loadData('familyMembers', []) || [];
    const member = members.find(function (m) { return m.id === selectedId; });
    const who = member ? (member.relation + (member.name ? '（' + member.name + '）' : '')) : '本人';
    const pairs = getRecentBpPairs(selectedId === '__self__' ? '本人' : selectedId);
    const last7 = pairs.slice(-7);
    const tasks = (A.loadData('collabTasks', []) || []).filter(function (t) {
      return !member || t.memberId === member.id;
    });

    let meanText = '暂无数据';
    let maxText = '—';
    let passText = '—';
    if (last7.length) {
      const ms = Math.round(last7.reduce(function (a, x) { return a + x.systolic; }, 0) / last7.length);
      const md = Math.round(last7.reduce(function (a, x) { return a + x.diastolic; }, 0) / last7.length);
      const maxP = last7.reduce(function (best, x) { return x.systolic > best.systolic ? x : best; }, last7[0]);
      const okCnt = last7.filter(function (x) { return x.systolic < 135 && x.diastolic < 85; }).length;
      meanText = ms + '/' + md + ' mmHg';
      maxText = maxP.systolic + '/' + maxP.diastolic + ' mmHg（' + maxP.date + '）';
      passText = okCnt + '/' + last7.length + ' 次（' + Math.round((okCnt / last7.length) * 100) + '%）';
    }

    const lines = [
      '【异地家庭慢病异步周报 · ' + isoOffset(6) + ' 至 ' + isoOffset(0) + '】',
      '关注成员：' + who + (member && member.conditions ? '｜' + member.conditions : ''),
      member && member.medications ? ('常规用药：' + member.medications) : '',
      '--------------------------------',
      '1. 血压监测摘要（近 ' + last7.length + ' 次记录）',
      '   · 平均血压：' + meanText,
      '   · 最高读数：' + maxText,
      '   · 家庭达标率（<135/85）：' + passText,
      '2. 异地协同事项（共 ' + tasks.length + ' 项）'
    ].filter(Boolean);

    tasks.slice(0, 5).forEach(function (t, i) {
      lines.push('   ' + (i + 1) + ') [' + (STATUS_LABELS[t.status] || t.status) + '] ' + t.title +
        (t.feedback ? '（反馈：' + t.feedback + '）' : ''));
    });
    lines.push('--------------------------------');
    lines.push('参考依据：《中国高血压防治指南（2024年修订版）》家庭自测阈值 135/85 mmHg。');
    lines.push('提示：本报告仅用于家庭监测与复诊参考，不构成医疗诊断。');

    document.getElementById('weeklyReportText').value = lines.join('\n');
    A.openMask(document.getElementById('weeklyReportMask'));
  }

  // ---------- 8. 视图切换与事件绑定 ----------
  function setViewMode(mode) {
    const isElder = mode === 'elder';
    const panel = document.getElementById('elderModePanel');
    if (panel) panel.hidden = !isElder;
    document.querySelectorAll('.mode-pill').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.viewMode === mode);
    });
    if (isElder && app()) {
      app().switchPage('data');
    }
  }

  function enhanceAssistantQuickPrompts() {
    const quick = document.getElementById('assistantQuick');
    if (!quick || quick.dataset.chronicEnhanced) return;
    quick.dataset.chronicEnhanced = '1';
    const extra = [
      { q: '爸爸这两天血压 146/92 需要注意什么？', label: '爸爸血压偏高怎么办（带指南溯源）' },
      { q: '爸爸早上测血压 156/96，忘吃氨氯地平，帮我记一下', label: '一句话记血压（触发草稿校验）' }
    ];
    extra.reverse().forEach(function (item) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.dataset.question = item.q;
      btn.textContent = item.label;
      quick.insertBefore(btn, quick.firstChild);
    });
  }

  function bindEvents() {
    const resetBtn = document.getElementById('resetGuestDemoBtn');
    if (resetBtn) {
      resetBtn.addEventListener('click', function () {
        ensureGuestSeed(true);
        if (app()) {
          app().refreshAllViews();
          app().showToast('已重置 14 天异地慢病家庭示例数据');
        }
      });
    }

    document.querySelectorAll('.mode-pill').forEach(function (btn) {
      btn.addEventListener('click', function () { setViewMode(btn.dataset.viewMode); });
    });
    const exitElder = document.getElementById('exitElderBtn');
    if (exitElder) exitElder.addEventListener('click', function () { setViewMode('standard'); });

    const chronicSel = document.getElementById('chronicMemberSelect');
    if (chronicSel) chronicSel.addEventListener('change', renderCollabDashboard);

    const openBpBtn = document.getElementById('openBpDraftBtn');
    if (openBpBtn) openBpBtn.addEventListener('click', function () { openBpDraft({ source: '快速录入' }); });

    const openReportBtn = document.getElementById('openWeeklyReportBtn');
    if (openReportBtn) openReportBtn.addEventListener('click', openWeeklyReportModal);

    const addTaskBtn = document.getElementById('addCollabTaskBtn');
    if (addTaskBtn) addTaskBtn.addEventListener('click', function () { openCollabTaskModal(null); });

    // 长辈极简录入按钮
    const bpInput = document.getElementById('bpMeterFileInput');
    const elderPhoto = document.getElementById('elderBpPhotoBtn');
    if (elderPhoto && bpInput) {
      elderPhoto.addEventListener('click', function () { bpInput.value = ''; bpInput.click(); });
    }
    const draftPhotoBtn = document.getElementById('bpDraftPhotoTrigger');
    if (draftPhotoBtn && bpInput) {
      draftPhotoBtn.addEventListener('click', function () { bpInput.value = ''; bpInput.click(); });
    }
    if (bpInput) {
      bpInput.addEventListener('change', function () {
        if (bpInput.files && bpInput.files[0]) handleBpMeterUpload(bpInput.files[0]);
      });
    }

    const elderVoiceBtn = document.getElementById('elderVoiceBpBtn');
    if (elderVoiceBtn) {
      elderVoiceBtn.addEventListener('click', function () {
        const inp = document.getElementById('elderQuickInput');
        if (inp) {
          if (!inp.value.trim()) inp.value = '爸爸早上测血压 152/94，忘吃氨氯地平，略微头晕';
          inp.focus();
        }
        const voiceFab = document.getElementById('voiceFab');
        if (voiceFab) voiceFab.click();
      });
    }

    const elderReportBtn = document.getElementById('elderReportBtn');
    if (elderReportBtn) {
      elderReportBtn.addEventListener('click', function () {
        const up = document.getElementById('quickReportUpload');
        if (up) up.click();
      });
    }

    const elderParseBtn = document.getElementById('elderQuickParseBtn');
    if (elderParseBtn) {
      elderParseBtn.addEventListener('click', function () {
        const raw = (document.getElementById('elderQuickInput').value || '').trim();
        const parsed = parseBpTextLocal(raw);
        if (!parsed) {
          if (app()) app().showToast('未识别到血压格式，请输入例如“爸爸早上测血压 148/92，已服药”');
          return;
        }
        openBpDraft(Object.assign({ source: '长辈一句话口语解析（待确认）' }, parsed));
      });
    }

    // 3 个评审一键模拟场景
    const demoClear = document.getElementById('demoBpClearBtn');
    if (demoClear) {
      demoClear.addEventListener('click', function () {
        openBpDraft({
          source: '血压计拍照模拟（清晰屏幕 · 置信度 95%）',
          member: 'm_dad', systolic: 148, diastolic: 92, pulse: 78,
          measuredPeriod: '晨起', medStatus: '未服药/漏服', symptom: '早起略感头胀',
          imageQuality: '清晰', confidence: 0.95
        });
      });
    }
    const demoGlare = document.getElementById('demoBpGlareBtn');
    if (demoGlare) {
      demoGlare.addEventListener('click', function () {
        openBpDraft({
          source: '血压计拍照模拟（反光倾斜难例 · 置信度 62%）',
          member: 'm_dad', systolic: 144, diastolic: 89, pulse: 76,
          measuredPeriod: '晚间', medStatus: '已服药',
          imageQuality: '反光或倾斜建议重拍', confidence: 0.62
        });
      });
    }
    const demoSpike = document.getElementById('demoBpSpikeBtn');
    if (demoSpike) {
      demoSpike.addEventListener('click', function () {
        openBpDraft({
          source: '血压计拍照模拟（历史基线突变测试）',
          member: 'm_dad', systolic: 174, diastolic: 106, pulse: 88,
          measuredPeriod: '晨起', medStatus: '未服药/漏服', symptom: '头晕明显',
          imageQuality: '清晰', confidence: 0.92
        });
      });
    }

    // 草稿弹窗事件
    ['bpDraftMember', 'bpDraftSys', 'bpDraftDia', 'bpDraftPulse'].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.addEventListener('input', runLiveDraftValidation);
      if (el) el.addEventListener('change', runLiveDraftValidation);
    });
    const bpClose = document.getElementById('bpDraftClose');
    const bpCancel = document.getElementById('bpDraftCancel');
    if (bpClose) bpClose.addEventListener('click', function () { app() && app().closeMask(document.getElementById('bpDraftMask')); });
    if (bpCancel) bpCancel.addEventListener('click', function () { app() && app().closeMask(document.getElementById('bpDraftMask')); });
    const bpSpeak = document.getElementById('bpSpeakBtn');
    if (bpSpeak) bpSpeak.addEventListener('click', speakBpDraft);
    const bpSave = document.getElementById('bpDraftSave');
    if (bpSave) bpSave.addEventListener('click', saveBpDraft);

    // 周报弹窗
    const wrClose = document.getElementById('weeklyReportClose');
    const wrCancel = document.getElementById('weeklyReportCancel');
    if (wrClose) wrClose.addEventListener('click', function () { app() && app().closeMask(document.getElementById('weeklyReportMask')); });
    if (wrCancel) wrCancel.addEventListener('click', function () { app() && app().closeMask(document.getElementById('weeklyReportMask')); });
    const wrCopy = document.getElementById('copyWeeklyReportBtn');
    if (wrCopy) {
      wrCopy.addEventListener('click', function () {
        const ta = document.getElementById('weeklyReportText');
        if (navigator.clipboard && ta) {
          navigator.clipboard.writeText(ta.value).then(function () {
            app() && app().showToast('已复制到剪贴板，可直接粘贴到微信发给家人');
          }).catch(function () {
            ta.select();
            document.execCommand('copy');
            app() && app().showToast('已复制周报内容');
          });
        } else if (ta) {
          ta.select();
          document.execCommand('copy');
          app() && app().showToast('已复制周报内容');
        }
      });
    }

    // 协同任务弹窗
    const ctClose = document.getElementById('collabTaskClose');
    const ctCancel = document.getElementById('collabTaskCancel');
    if (ctClose) ctClose.addEventListener('click', function () { app() && app().closeMask(document.getElementById('collabTaskMask')); });
    if (ctCancel) ctCancel.addEventListener('click', function () { app() && app().closeMask(document.getElementById('collabTaskMask')); });
    const ctSave = document.getElementById('collabTaskSave');
    if (ctSave) ctSave.addEventListener('click', saveCollabTaskModal);
  }

  function renderAll() {
    updateDemoBar();
    renderCollabDashboard();
    enhanceAssistantQuickPrompts();
  }

  window.HM_CHRONIC = {
    ensureGuestSeed: ensureGuestSeed,
    renderAll: renderAll,
    openBpDraft: openBpDraft,
    buildLocalReply: buildLocalReply,
    setViewMode: setViewMode
  };

  bindEvents();
  renderAll();
})();
