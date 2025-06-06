<!--
 *  =======================================================================
 *  ·······································································
 *  ·······································································
 *  ····Y88b···d88P················888b·····d888·d8b·······················
 *  ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 *  ······Y88o88P··················88888b·d88888···························
 *  ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 *  ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 *  ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 *  ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 *  ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 *  ·······························································888·····
 *  ··························································Y8b·d88P·····
 *  ···························································"Y88P"······
 *  ·······································································
 *  =======================================================================
 * 
 *  -----------------------------------------------------------------------
 * Author       : 焱铭
 * Date         : 2025-04-24 12:33:13 +0800
 * LastEditTime : 2025-05-23 20:18:07 +0800
 * Github       : https://github.com/YanMing-lxb/
 * FilePath     : /RefrTruck-HeatLoad-Solver/CHANGELOG.md
 * Description  : 
 *  -----------------------------------------------------------------------
 -->

# CHANGELOG

<!-- ### 新增功能
- 添加了对新文件格式的支持。
- 增加了自动保存功能，防止数据丢失。

### 改进
- 优化了代码结构，提升了运行效率。
- 改进了用户界面，使其更加直观易用。

### 修复
- 修复了在特定情况下程序崩溃的问题。
- 修正了若干已知的bug。

### 其他
- 新增 CHANGELOG.md 文件，用于记录版本更新日志。
 -->

## v0.1.0

### 🎉 新增

- 增加冷藏车辆默认长度推荐下拉框，预设常用冷藏车厢体尺寸参数
- 新增GUI显示模式，默认为应用默认参数的极简模式，可通过 `高级` 选项进行更为详细的参数输入
- 新增 `详细输出` 标签栏，用于详细展示各部分热负荷计算结果，同样有 `结果输出` 用于显示主要计算结果
- 新增日间模式夜间模式切换按钮
- 新增配置文件，可以通过配置文件更改预置的数据
- 新增产品推荐功能：根据程序输入温度以及计算负荷，推荐产品，其中产品性能则根据录入数据进行二维插值获取。

### 🌟 改进

- 改进带有预设数据组件的GUI布置逻辑，精简显示
- 优化精简GUI界面，调整界面大小
- 调整冷藏货物和冷冻货物的预设数据排序，按照冷链运输量来进行排序，并默认显示运输量最高的数据
- 更改打包方式，方便配置文件的修改
- 改善功能按钮的显示效果，改进颜色图标的显示
- 环境温度、冷藏温度、冷冻温度和出库温度改为具有下拉框的选项

## v0.0.7

### 🎉 新增

- 新增工具函数用于辅助版本管理

## v0.0.6

### 🌟 改进

- 优化输入提示信息

### 🐛 修复

- 修正厢体参数中输入单个值时，程序报错的问题
- 改正报错逻辑，出错时终止程序运行

## v0.0.5

### 🐛 修复

- 改正中国各地太阳辐照强度
- 统一gui中负荷输出的位置

## v0.0.4

### 🐛 修复

- 改正各层密度提示信息

## v0.0.3

### 🐛 修复

- 太阳辐照强度，默认值采用 QX/T368—2016 1366.1W/m²

## v0.0.2

### 🎉 新增

- 新增程序打包脚本
- 新增太阳辐射预设数据
- 新增各种材料辐射率和吸收率参数
- 新增各种货物参数
- 新增冷藏车尺寸示意图并完善三种模式切换间的显示逻辑

### 🐛 修复

- 冷冻总负荷标签显示不正确
- 主界面去掉 LOGO
- 去掉玻尔兹曼常数输入框，改为内置

## v0.0.1

### 🎉 新增

- 考虑车厢预冷的情况，考虑预冷时间
- 考虑冷藏货物预冷的情况，冷藏货物预冷时间与车厢预冷时间相同
- 程序中车厢外表面温度通过牛顿拉夫逊法迭代求解太阳辐射和对流导致的温度变化
- 考虑电气热负荷计算，考虑风机功率和照明功率
- 程序内部已集成干空气物性参与湿空气物性参数计算功能
- 增加对流换热系数高级功能

  - 考虑厢体材料各层厚度，物性参数等对传热系数影响
  - 考虑厢体内部自然对流
  - 考虑热桥影响，通过设置热桥系数实现

### 🐛 修复

- 车厢内部尺寸长宽高计算调整为，外部尺寸-2倍厚度
- 修正车原计算公式为行驶漏热量乘安全系数，改正后安全系数乘最终负荷
- 重写计算太阳辐射部分计算逻辑
