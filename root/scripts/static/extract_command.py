<!-- ====== 新建脚本弹窗 ====== -->
<div class="modal active" id="newModal" style="display:flex;">
<div class="modal-box">
<span class="close" onclick="closeModalByName('newModal')">&times;</span>
<h2>📝 新建脚本</h2>
<div style="margin:12px 0"><label>文件名（.py）</label><input type="text" id="newName" placeholder="例如: monitor.py"></div>
<div><label>代码内容</label><textarea id="newContent" placeholder="# 在此编写 Python 代码"></textarea></div>
<div class="form-actions"><button class="btn-primary" onclick="createScript()">💾 保存</button><button class="btn-secondary" onclick="closeModalByName('newModal')">取消</button></div>
</div>
</div>

<!-- ====== 编辑脚本弹窗 ====== -->
<div class="modal active" id="editModal" style="display:none;">
<div class="modal-box">
<span class="close" onclick="closeModalByName('editModal')">&times;</span>
<h2>✏️ 编辑脚本</h2>
<div style="margin:12px 0">
<label>选择脚本</label>
<select id="editSelect" onchange="loadEditContent()"></select>
</div>
<div><label>代码内容</label><textarea id="editContent"></textarea></div>
<div class="form-actions"><button class="btn-primary" onclick="saveEdit()">💾 保存</button><button class="btn-secondary" onclick="closeModalByName('editModal')">取消</button></div>
</div>
</div>

<!-- ====== 删除脚本弹窗 ====== -->
<div class="modal active" id="delModal" style="display:none;">
<div class="modal-box">
<span class="close" onclick="closeModalByName('delModal')">&times;</span>
<h2>🗑 删除脚本</h2>
<div style="margin:12px 0">
<label>选择要删除的脚本</label>
<select id="delSelect"></select>
</div>
<div class="form-actions"><button class="btn-danger" onclick="deleteScript()">🗑 确认删除</button><button class="btn-secondary" onclick="closeModalByName('delModal')">取消</button></div>
</div>
</div>

<!-- ====== 上传脚本弹窗 ====== -->
<div class="modal active" id="uploadModal" style="display:none;">
<div class="modal-box" style="max-width:500px;width:94%;">
<span class="close" onclick="closeModalByName('uploadModal')">&times;</span>
<h2>📤 上传脚本</h2>
<div style="margin:16px 0;">
    <label style="font-weight:500;font-size:14px;color:#555;display:block;margin-bottom:6px;">选择 .py 文件</label>
    <input type="file" id="uploadFileInput" accept=".py" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;font-size:14px;background:#fff;">
    <div style="font-size:12px;color:#888;margin-top:6px;">💡 只支持 .py 文件，同名文件会被覆盖</div>
</div>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:8px;">
    <button class="btn-primary" onclick="doUpload()" style="padding:8px 28px;border:none;border-radius:6px;cursor:pointer;font-weight:500;background:#667eea;color:#fff;font-size:14px;">📤 上传</button>
    <button class="btn-secondary" onclick="closeModalByName('uploadModal')" style="padding:8px 20px;border:none;border-radius:6px;cursor:pointer;font-weight:500;background:#eceff1;color:#333;font-size:14px;">取消</button>
</div>
<pre id="uploadOutput" style="margin-top:12px;background:#1e1e1e;color:#d4d4d4;padding:12px;border-radius:6px;font-size:12px;max-height:200px;overflow:auto;white-space:pre-wrap;word-break:break-all;display:none;">执行中...</pre>
</div>
</div>

<!-- ====== 查看日志弹窗 ====== -->
<div class="modal active" id="logModal" style="display:none;">
<div class="modal-box">
<span class="close" onclick="closeModalByName('logModal')">&times;</span>
<h2>📄 查看日志</h2>
<div style="margin:12px 0">
<label>选择脚本</label>
<select id="logSelect" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;font-size:14px;background:#fff;"></select>
</div>
<pre id="logContent" style="background:#1e1e1e;color:#d4d4d4;padding:12px;border-radius:6px;font-size:12px;max-height:300px;overflow:auto;white-space:pre-wrap;word-break:break-all">请选择脚本</pre>
<div style="margin-top:12px;text-align:right;">
    <button class="btn-secondary" onclick="closeModalByName('logModal')" style="padding:6px 20px;border:none;border-radius:6px;cursor:pointer;font-weight:500;background:#eceff1;">关闭</button>
</div>
</div>
</div>

<!-- ====== 同步脚本弹窗 ====== -->
<div class="modal active" id="syncModal" style="display:none;">
<div class="modal-box" style="max-width:600px;width:94%;">
<span class="close" onclick="closeModalByName('syncModal')">&times;</span>
<h2>📥 从 GitHub 同步脚本</h2>
<div style="margin:16px 0;">
    <label style="font-weight:500;font-size:14px;color:#555;display:block;margin-bottom:6px;">仓库地址</label>
    <input type="text" id="syncRepoInput" placeholder="https://github.com/用户名/仓库名" style="width:100%;padding:10px 14px;border:1px solid #ddd;border-radius:6px;font-size:14px;font-family:monospace;">
    <div style="font-size:12px;color:#888;margin-top:6px;">💡 支持公开仓库和私有仓库（带 Token），修改后自动保存</div>
</div>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:8px;">
    <button class="btn-primary" onclick="doSync()" style="padding:8px 28px;border:none;border-radius:6px;cursor:pointer;font-weight:500;background:#667eea;color:#fff;font-size:14px;">📥 开始同步</button>
    <button class="btn-secondary" onclick="closeModalByName('syncModal')" style="padding:8px 20px;border:none;border-radius:6px;cursor:pointer;font-weight:500;background:#eceff1;color:#333;font-size:14px;">取消</button>
</div>
<pre id="syncOutput" style="margin-top:12px;background:#1e1e1e;color:#d4d4d4;padding:12px;border-radius:6px;font-size:12px;max-height:200px;overflow:auto;white-space:pre-wrap;word-break:break-all;display:none;">执行中...</pre>
</div>
</div>

<!-- ====== 定时任务弹窗 ====== -->
<div class="modal active" id="cronModal" style="display:none;">
<div class="modal-box" style="max-width:720px;width:94%;">
<span class="close" onclick="closeModalByName('cronModal')">&times;</span>
<h2>⏰ 定时任务管理</h2>

<div style="margin:12px 0;background:#f5f7fa;padding:16px;border-radius:8px;">

    <div style="margin-bottom:12px;">
        <label style="font-weight:500;font-size:13px;color:#555;display:block;margin-bottom:4px;">执行模式</label>
        <select id="cronMode" onchange="cronModeChange()" style="width:100%;padding:8px 12px;border:1px solid #ddd;border-radius:6px;font-size:14px;background:#fff;">
            <option value="custom">🔧 自定义 (Cron表达式)</option>
            <option value="daily">📅 每天</option>
            <option value="weekly">📅 每周</option>
            <option value="hourly">⏰ 每小时</option>
            <option value="minutes">⏱️ 每N分钟</option>
        </select>
    </div>

    <div id="cronDaily" style="display:none;margin-bottom:12px;">
        <label style="font-weight:500;font-size:13px;color:#555;display:block;margin-bottom:4px;">每天执行时间</label>
        <select id="cronDailyHour" style="width:60px;padding:6px 8px;border:1px solid #ddd;border-radius:4px;font-size:14px;display:inline-block;margin-right:4px;">
            <option value="0">00</option><option value="1">01</option><option value="2">02</option><option value="3">03</option>
            <option value="4">04</option><option value="5">05</option><option value="6">06</option><option value="7">07</option>
            <option value="8">08</option><option value="9">09</option><option value="10">10</option><option value="11">11</option>
            <option value="12">12</option><option value="13">13</option><option value="14">14</option><option value="15">15</option>
            <option value="16">16</option><option value="17">17</option><option value="18">18</option><option value="19">19</option>
            <option value="20">20</option><option value="21">21</option><option value="22">22</option><option value="23">23</option>
        </select>时
        <select id="cronDailyMinute" style="width:60px;padding:6px 8px;border:1px solid #ddd;border-radius:4px;font-size:14px;display:inline-block;margin-left:4px;margin-right:4px;">
            <option value="0">00</option><option value="1">01</option><option value="2">02</option><option value="3">03</option>
            <option value="4">04</option><option value="5">05</option><option value="6">06</option><option value="7">07</option>
            <option value="8">08</option><option value="9">09</option><option value="10">10</option><option value="11">11</option>
            <option value="12">12</option><option value="13">13</option><option value="14">14</option><option value="15">15</option>
            <option value="16">16</option><option value="17">17</option><option value="18">18</option><option value="19">19</option>
            <option value="20">20</option><option value="21">21</option><option value="22">22</option><option value="23">23</option>
            <option value="24">24</option><option value="25">25</option><option value="26">26</option><option value="27">27</option>
            <option value="28">28</option><option value="29">29</option><option value="30">30</option><option value="31">31</option>
            <option value="32">32</option><option value="33">33</option><option value="34">34</option><option value="35">35</option>
            <option value="36">36</option><option value="37">37</option><option value="38">38</option><option value="39">39</option>
            <option value="40">40</option><option value="41">41</option><option value="42">42</option><option value="43">43</option>
            <option value="44">44</option><option value="45">45</option><option value="46">46</option><option value="47">47</option>
            <option value="48">48</option><option value="49">49</option><option value="50">50</option><option value="51">51</option>
            <option value="52">52</option><option value="53">53</option><option value="54">54</option><option value="55">55</option>
            <option value="56">56</option><option value="57">57</option><option value="58">58</option><option value="59">59</option>
        </select>分
    </div>

    <div id="cronWeekly" style="display:none;margin-bottom:12px;">
        <div style="margin-bottom:6px;">
            <label style="font-weight:500;font-size:13px;color:#555;display:block;margin-bottom:4px;">每周几执行</label>
            <select id="cronWeeklyDay" style="width:100%;padding:6px 10px;border:1px solid #ddd;border-radius:4px;font-size:14px;">
                <option value="0">周日</option>
                <option value="1">周一</option>
                <option value="2">周二</option>
                <option value="3">周三</option>
                <option value="4">周四</option>
                <option value="5">周五</option>
                <option value="6">周六</option>
            </select>
        </div>
        <div>
            <label style="font-weight:500;font-size:13px;color:#555;display:block;margin-bottom:4px;">执行时间</label>
            <select id="cronWeeklyHour" style="width:60px;padding:6px 8px;border:1px solid #ddd;border-radius:4px;font-size:14px;display:inline-block;margin-right:4px;">
                <option value="0">00</option><option value="1">01</option><option value="2">02</option><option value="3">03</option>
                <option value="4">04</option><option value="5">05</option><option value="6">06</option><option value="7">07</option>
                <option value="8">08</option><option value="9">09</option><option value="10">10</option><option value="11">11</option>
                <option value="12">12</option><option value="13">13</option><option value="14">14</option><option value="15">15</option>
                <option value="16">16</option><option value="17">17</option><option value="18">18</option><option value="19">19</option>
                <option value="20">20</option><option value="21">21</option><option value="22">22</option><option value="23">23</option>
            </select>时
            <select id="cronWeeklyMinute" style="width:60px;padding:6px 8px;border:1px solid #ddd;border-radius:4px;font-size:14px;display:inline-block;margin-left:4px;margin-right:4px;">
                <option value="0">00</option><option value="1">01</option><option value="2">02</option><option value="3">03</option>
                <option value="4">04</option><option value="5">05</option><option value="6">06</option><option value="7">07</option>
                <option value="8">08</option><option value="9">09</option><option value="10">10</option><option value="11">11</option>
                <option value="12">12</option><option value="13">13</option><option value="14">14</option><option value="15">15</option>
                <option value="16">16</option><option value="17">17</option><option value="18">18</option><option value="19">19</option>
                <option value="20">20</option><option value="21">21</option><option value="22">22</option><option value="23">23</option>
                <option value="24">24</option><option value="25">25</option><option value="26">26</option><option value="27">27</option>
                <option value="28">28</option><option value="29">29</option><option value="30">30</option><option value="31">31</option>
                <option value="32">32</option><option value="33">33</option><option value="34">34</option><option value="35">35</option>
                <option value="36">36</option><option value="37">37</option><option value="38">38</option><option value="39">39</option>
                <option value="40">40</option><option value="41">41</option><option value="42">42</option><option value="43">43</option>
                <option value="44">44</option><option value="45">45</option><option value="46">46</option><option value="47">47</option>
                <option value="48">48</option><option value="49">49</option><option value="50">50</option><option value="51">51</option>
                <option value="52">52</option><option value="53">53</option><option value="54">54</option><option value="55">55</option>
                <option value="56">56</option><option value="57">57</option><option value="58">58</option><option value="59">59</option>
            </select>分
        </div>
    </div>

    <div id="cronHourly" style="display:none;margin-bottom:12px;">
        <label style="font-weight:500;font-size:13px;color:#555;display:block;margin-bottom:4px;">每小时第几分钟执行</label>
        <select id="cronHourlyMinute" style="width:60px;padding:6px 8px;border:1px solid #ddd;border-radius:4px;font-size:14px;">
            <option value="0">00</option><option value="1">01</option><option value="2">02</option><option value="3">03</option>
            <option value="4">04</option><option value="5">05</option><option value="6">06</option><option value="7">07</option>
            <option value="8">08</option><option value="9">09</option><option value="10">10</option><option value="11">11</option>
            <option value="12">12</option><option value="13">13</option><option value="14">14</option><option value="15">15</option>
            <option value="16">16</option><option value="17">17</option><option value="18">18</option><option value="19">19</option>
            <option value="20">20</option><option value="21">21</option><option value="22">22</option><option value="23">23</option>
            <option value="24">24</option><option value="25">25</option><option value="26">26</option><option value="27">27</option>
            <option value="28">28</option><option value="29">29</option><option value="30">30</option><option value="31">31</option>
            <option value="32">32</option><option value="33">33</option><option value="34">34</option><option value="35">35</option>
            <option value="36">36</option><option value="37">37</option><option value="38">38</option><option value="39">39</option>
            <option value="40">40</option><option value="41">41</option><option value="42">42</option><option value="43">43</option>
            <option value="44">44</option><option value="45">45</option><option value="46">46</option><option value="47">47</option>
            <option value="48">48</option><option value="49">49</option><option value="50">50</option><option value="51">51</option>
            <option value="52">52</option><option value="53">53</option><option value="54">54</option><option value="55">55</option>
            <option value="56">56</option><option value="57">57</option><option value="58">58</option><option value="59">59</option>
        </select>分
        <div style="font-size:12px;color:#888;margin-top:4px;">💡 例如: 选择 30，则每小时 30 分执行</div>
    </div>

    <div id="cronMinutes" style="display:none;margin-bottom:12px;">
        <label style="font-weight:500;font-size:13px;color:#555;display:block;margin-bottom:4px;">每</label>
        <select id="cronMinutesInterval" style="width:80px;padding:6px 8px;border:1px solid #ddd;border-radius:4px;font-size:14px;display:inline-block;margin-right:4px;">
            <option value="5">5</option>
            <option value="10">10</option>
            <option value="15" selected>15</option>
            <option value="20">20</option>
            <option value="30">30</option>
            <option value="60">60</option>
        </select>分钟执行一次
        <div style="font-size:12px;color:#888;margin-top:4px;">💡 例如: 选择 15，则每 15 分钟执行一次</div>
    </div>

    <div id="cronCustom" style="margin-bottom:12px;">
        <label style="font-weight:500;font-size:13px;color:#555;display:block;margin-bottom:4px;">Cron 表达式</label>
        <input type="text" id="cronSchedule" placeholder="分 时 日 月 周" value="0 */6 * * *" style="width:100%;padding:8px 12px;border:1px solid #ddd;border-radius:6px;font-size:14px;font-family:monospace;">
        <div style="font-size:12px;color:#888;margin-top:4px;">💡 格式: 分 时 日 月 周 | 示例: <code>0 */6 * * *</code> = 每6小时</div>
    </div>

    <div style="margin-bottom:12px;">
        <label style="font-weight:500;font-size:13px;color:#555;display:block;margin-bottom:4px;">执行命令</label>
        <select id="cronCommandSelect" style="width:100%;padding:8px 12px;border:1px solid #ddd;border-radius:6px;font-size:14px;background:#fff;margin-bottom:6px;">
            <option value="">-- 选择脚本 --</option>
        </select>
        <input type="text" id="cronCustomCmd" placeholder="或直接输入完整命令" style="width:100%;padding:8px 12px;border:1px solid #ddd;border-radius:6px;font-size:14px;font-family:monospace;">
    </div>

    <button class="btn-success" onclick="cronAdd()" style="width:100%;padding:10px;border:none;border-radius:6px;cursor:pointer;font-weight:500;background:#4caf50;color:#fff;font-size:14px;">➕ 添加任务</button>
</div>

<div style="margin-top:16px;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <label style="font-weight:500;font-size:14px;color:#555;">📋 当前任务列表</label>
        <button class="btn-secondary" onclick="cronRefreshList()" style="padding:4px 14px;border:none;border-radius:4px;cursor:pointer;font-size:12px;background:#eceff1;">🔄 刷新</button>
    </div>
    <div id="cronListContainer" style="max-height:300px;overflow-y:auto;border:1px solid #eee;border-radius:8px;background:#fff;">
        <div style="color:#999;padding:20px;text-align:center;">点击「刷新」加载任务</div>
    </div>
</div>

<div style="margin-top:16px;text-align:right;">
    <button class="btn-secondary" onclick="closeModalByName('cronModal')" style="padding:6px 24px;border:none;border-radius:6px;cursor:pointer;font-weight:500;background:#eceff1;">关闭</button>
</div>
</div>
</div>
