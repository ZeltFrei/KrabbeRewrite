# Krabbe 2.0〡自動化語音&音樂系統

現在馬上試用語音功能：https://discord.gg/2uQj5uWSqB
如果您喜歡此機器人，可以聯絡KiziRay

## 目前狀態

主要功能已經全數完成，包含語音建立、設定、紀錄、音樂等...

### DONE

- 頻道主控面板
- 頻道紀錄方式
- 頻道隨機密碼鎖
- 個別調整機器人設定
- 安裝導覽系統
- 機器人授權訊息
- 子機器音樂功能 [Kava](https://github.com/ZeltFrei/Kava)

### TODOs
- 音樂功能新增、優化
- 各項功能優化、除錯

### FUTURE
- 未定

## 功能簡介

- 用戶可以自行創建語音頻道，頻道擁有者為頻道建立者
- 頻道的擁有者可以對語音頻道進行各項語音設定
- 用戶可以在語音頻道播放各大平台的音樂
- 用戶可以為語音頻道建立鎖定

## 系統安裝

1. 用戶使用 /start 命令來執行安裝導覽
2. 根據導覽說明進行操作
3. 完成各頻道的權限設定

## 建立頻道

1. 用戶加入名為「建立語音頻道」的語音頻道
2. 自動創建一個語音頻道，並自動套用儲存的頻道設定
3. 將用戶轉移至創建好的語音頻道

## 預設系統頻道

系統會自動建立四個頻道，分別為
1. 語音事件紀錄：此論壇頻道用於紀錄所有語音的動態，包含成員語音設定，任何加入、退出等資訊。
2. 語音訊息紀錄：此論壇頻道用於紀錄所有語音文字頻道中的所有發佈的訊息紀錄（不包含語音設定）。
3. 語音控制面板：此文字頻道用於成員設定自己的語音頻道相關內容。
4. 建立語音頻道：此語音頻道用於自動建立語音頻道，並根據用戶名稱來設定頻道名稱。

## 音樂系統

用戶最多可以邀請三個子機器人來播放語音音樂，分別為 [Melod](https://discord.com/oauth2/authorize?client_id=1239105289299431464),[Harmony](https://discord.com/oauth2/authorize?client_id=1239137607884210226),[Rhythms](https://discord.com/oauth2/authorize?client_id=1239137639605604414)
1. 在語音頻道使用 /py 命令來播放音樂
2. 系統會自動分派三個子機的其中一台
3. 一個伺服器不同語音頻道最多可以同時播放三台音樂機器人

## 頻道的「生命週期」

一個頻道的生命週期自**創建**開始，**刪除**結束，有以下幾個狀態

- **準備中**：頻道剛被創建，正在執行設定步驟，並在準備完成時使擁有者加入並進入**使用中**
- **使用中**：頻道大多數時間都處於這個狀態，所有者可在這個狀態中對頻道進行設定
- **待轉移**：頻道所有者離開了語音頻道且頻道中尚有成員，進入 60 秒倒數，若頻道擁有者沒有在期間內回來，將頻道所有權移轉給頻道內隨機成員，並套用該成員儲存的所有設定，並回到**使用中**
- **待刪除**：所有成員都離開了頻道，進入 60 秒倒數，若在期間內有成員加入頻道，則直接取得頻道的所有權並使頻道回到**使用中**
- **刪除**：**待刪除**倒數結束，移除頻道

## 頻道鎖

頻道擁有者可以選擇為自己的頻道上鎖，使用密碼保護自己的頻道
成員加入頻道時，需要點擊一個按鈕並選擇要加入的頻道，輸入密碼以取得權限

#### 加入頻道流程

1. 點擊控制面板的加入私人語音按鈕
2. 向擁有者取得6位數隨機PIN碼
3. 進入語音頻道並獲得權限

## 設定

頻道設定分為以下幾類，頻道進行設定前，會要求設定成員建立語音頻道或成為擁有者，並接受授權書(雙語言版本，如圖)
![image](https://github.com/ZeltFrei/KrabbeRewrite/assets/89194114/ae24fee8-a15b-451c-a015-dd02d7f18173)
![image](https://github.com/ZeltFrei/KrabbeRewrite/assets/89194114/39adf417-ef04-402d-ab6b-b582986f7e38)

#### 頻道設定

- 重新命名
- 移交所有權
- 移除頻道

#### 成員設定

- 邀請成員
- 移出成員
- 頻道鎖
- 人數限制
- 進出通知

#### 語音設定

- 語音比特率
- 是否開啟 NSFW
- 是否允許使用音效版
- 是否開啟文字頻道
- 是否允許傳送媒體
- 文字頻道的慢速模式
- 語音伺服器區域
- 是否允許成員直播
- 是否允許建立語音活動

#### 音樂設定

 - 隨機播放音樂
 - 是否允許成員操控頻道音樂
 - 調整音樂音量

另外，所有設定都將被自動保存，並在任何成員成為頻道所有者時自動套用

## 設置

- 透過 /start 命令來使機器人自動完成有關這個伺服器的所有設置
- 每個設定面板都是獨立的值，可以透過 /panel 命令來重新傳送面板
- 透過 /configure 命令來設定系統的內部設定，僅限伺服器管理員&擁有者

## 授權機制

透過 [EvanlauOauthServer](https://github.com/ZeltFrei/EvanlauOauthServer) 存取 Qlipoth 的成員驗證資料庫，僅限已驗證的成員可以使用設定

## 開發人員
功能編寫：[ @ne](https://github.com/Nat1anWasTaken) ![image](https://github.com/ZeltFrei/KrabbeRewrite/assets/89194114/7d8a792c-2db1-4956-a539-86637e5b7d54)

系統設計：[KiziRay](https://github.com/KiziRay) ![image](https://github.com/ZeltFrei/KrabbeRewrite/assets/89194114/099590f7-3b59-496e-82f4-083998295a56)

授權系統：[Evanlau1798](https://github.com/Evanlau1798) ![image](https://github.com/ZeltFrei/KrabbeRewrite/assets/89194114/dd9eabc4-dcfc-4a93-b567-9930adfa8362)

> 此機器人的代碼是公開的，但未經開發人員授權禁止使用，僅供閱讀查看。
The Repository is public but cannot be used without the developer's authorization and is for reading only.
