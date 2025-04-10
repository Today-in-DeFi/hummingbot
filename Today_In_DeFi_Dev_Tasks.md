# Today In DeFi 分叉開發工作


---

## 🔧 下一階段任務優先順序

### ✅ 第一階段（已完成）
| 優先級 | 任務 | 狀態 |
|--------|------|------|
| 🔴 High | 加入 `try/except` 保護與關鍵日誌記錄 | ✅ 已完成並合併 PR |

---

### 🟡 第二階段（進行中／推薦現在開始）
| 優先級 | 任務 | 說明 |
|--------|------|------|
| 🟡 High | **交易費用設定選項化** | 允許使用者選擇使用 taker/maker 費率，並動態計算成本。需修改 `get_current_profitability_after_fees()`。 → 影響盈利判斷與風控。 |
| 🟡 High | **補上 `self.ready_to_trade = True`** | 加入到 `start()` 內，確保 `format_status()` 顯示正確狀態。影響 UI 顯示與 debug 便利性。 |
| 🟡 Medium | **將 `get_most_profitable_combination()` 回傳改為清單** | 可回傳所有符合利差條件的交易對組合，排序後依序檢查，增加多樣選擇機會。建議用 `heapq.nlargest()`。 |

---

### 🟢 第三階段（架構優化與進階功能）
| 優先級 | 任務 | 說明 |
|--------|------|------|
| 🟢 Medium | **改用雙邊價格平均估算 Position Size** | 避免只依賴 `connector_1` 導致錯誤，改用雙邊 mid price。需調整 `get_position_executors_config()`。 |
| 🟢 Medium | **改善平倉條件設計** | 改用「移動式停利 + 停損」組合邏輯，提升出場決策的彈性與安全性。可參考 `trailing_stop` 演算法設計。

| 🟢 Medium | **資金費率歷史預測機制** |  
使用過去資金費率計算趨勢線或滑動平均，預測未來 8 小時的趨勢。可簡單先用 EMA。

---

### ⚪ 第四階段（細節與風險處理）
| 優先級 | 任務 | 說明 |
|--------|------|------|
| ⚪ Low | **改善型別定義與預設值** | 例如 `token_whitelist` 使用 `Set[str]` 且預設為 `{"WIF", "FET"}`。 |
| ⚪ Low | **變數命名更直觀** | 將 `funding_rate_diff_stop_loss` 改為 `min_funding_rate_diff_to_stop` 等。 |
| ⚪ Low | **處理負的 TP 天數顯示問題** | 避免在 `Days to TP` 顯示負數值，引導使用者做出誤判。 |

---

## ✅ 推薦下一步行動（建議現在做）
- 選擇其中 1~2 項開始撰寫功能分支（如 `feat/fee-config-option`）
- 我可以幫你產出：  
	- 修改範圍說明  
	- code scaffolding（空殼程式碼）  
	- commit message 建議  
	- PR 描述模版  
	- diff patch 格式

你希望我先幫你處理哪一個任務？我可以立即幫你開第一個 task 👇