# Krabbe II

## 功能簡介

- 用戶可創建擁有自己的語音頻道
- 頻道的擁有者可以對語音頻道進行設定

## 建立頻道

1. 用戶加入「建立語音頻道」
2. 創建一個語音頻道，並套用用戶先前儲存的設定
3. 將用戶轉移至創建好的語音頻道

## 頻道的「生命週期」

一個頻道的生命週期自**創建**開始，**刪除**結束，有以下幾個狀態

- **準備中**：頻道剛被創建，正在執行設定步驟，並在準備完成時使擁有者加入並進入**使用中**
- **使用中**：頻道大多數時間都處於這個狀態，所有者可在這個狀態中對頻道進行設定
- **待轉移**：頻道所有者離開了語音頻道且頻道中尚有成員，進入 60 秒倒數，若頻道擁有者沒有在期間內回來，將頻道所有權移轉給頻道內隨機成員並回到
  **使用中**
- **待刪除**：所有成員都離開了頻道，進入 60 秒倒數，若在期間內有成員加入頻道，則直接取得頻道的所有權並使頻道回到**使用中**
- **刪除**：**待刪除**倒數結束，移除頻道

## 頻道鎖

頻道擁有者可以選擇為自己的頻道上鎖，使用密碼保護自己的頻道
成員加入頻道時，需要點擊一個按鈕並選擇要加入的頻道，輸入密碼以取得權限

#### 加入頻道流程

1. 點擊指定按鈕
2. 輸入密碼
3. 取得頻道權限

## 設定

頻道設定分為以下幾類

#### 頻道設定

- 重新命名
- 頻道狀態 (Activity)
- 移交所有權
- 移除頻道

#### 成員設定

- 邀請成員
- 移出成員
- 頻道鎖
- 人數限制

#### 語音設定

- 是否允許使用音效版
- 是否開啟文字頻道
- 是否允許傳送媒體
- 文字頻道的慢速模式

另外，所有設定都將被自動保存，並在任何成員成為頻道所有者時自動套用

## 初次設置

- 一鍵設置指令，機器人會自動完成有關這個伺服器的所有設置
- 每個面板都會有獨立的指令方便傳送

## 使用授權

透過 [EvanlauOauthServer](https://github.com/ZeltFrei/EvanlauOauthServer) 存取 Qlipoth 的成員驗證資料庫，僅限已驗證的成員可以使用