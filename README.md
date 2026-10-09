# THHT Study Prototype

A course prototype of an online experiment using the Tangram Help/Hurt Task (THHT), with a researcher dashboard.

本项目是一个使用七巧板帮助/伤害任务（THHT）的在线实验课程原型，并附有研究者统计面板。

## Pages

- `index.html`: landing page.
  - 首页。
- `experiment.html`: the experiment (English with Chinese translation).
  - 实验（英文附中文翻译）。
- `experiment-en.html`: the experiment (English only).
  - 实验（纯英文版）。
- `dashboard.html`: researcher dashboard.
  - 研究者统计面板。

## Important

This is a teaching prototype. No responses are sent to or stored on a server.

这是一个教学原型。作答不会发送或保存到任何服务器。

The dashboard shows **simulated demo data** (60 generated participants), not real responses. Real session JSON files saved from the experiment can be imported in the browser; they stay on your computer.

统计面板显示的是**模拟演示数据**（60名生成的参与者），并非真实作答。可以在浏览器中导入从实验保存的真实会话 JSON 文件；这些文件仅保留在您的电脑上。

The dashboard loads Chart.js from the jsDelivr CDN.

统计面板通过 jsDelivr CDN 加载 Chart.js。
