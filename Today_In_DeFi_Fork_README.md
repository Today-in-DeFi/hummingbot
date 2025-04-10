# Hummingbot - Today In DeFi Fork

## 🧭 專案簡介 / Project Overview

本文件記錄我們針對 **Hummingbot** 策略腳本 `v2_funding_rate_arb.py` 的開發任務。此策略是為了透過不同交易所之間的資金費率差異進行套利操作，然而原始實作在**利潤計算準確性、風險控制機制、邏輯彈性與錯誤容錯能力**等方面仍有改進空間。

我們透過分階段任務設計，針對下列問題逐步進行強化：

- 僅考慮當前資金費率，缺乏預測性與風險緩衝機制
- 假設固定交易費率，未區分 taker/maker 模式
- 回傳結果只考慮單一組合，限制策略多樣性
- 缺乏錯誤處理與資料驗證，難以偵錯或自我保護
- 程式結構不易擴充，不利於內部模組或邏輯重用

透過這個開發計畫，我們希望提升策略的**可靠性、彈性與真實可用性**，並為後續開發更進階的 DeFi 策略（如多市場多幣種資金費率套利、期現套利等）奠定穩固基礎。

---

This document tracks the internal development roadmap for improving the Hummingbot strategy script `v2_funding_rate_arb.py`. The strategy aims to exploit funding rate differences across exchanges. However, the original implementation has limitations in **profit estimation accuracy, risk control, logical flexibility, and robustness**.

Our phased development plan addresses issues such as:

- No forecasting of funding rates — overly reactive
- Hardcoded taker fees — no support for maker/mixed modes
- Only one arbitrage pair evaluated — not scalable for multi-pair
- Lack of error handling and market data validation
- Rigid structure — limits future modularization or reuse

By executing this roadmap, we aim to improve the **reliability, adaptability, and deployability** of the strategy, and lay a solid foundation for future advanced DeFi strategies (e.g., multi-leg arbitrage, cross-market hedging).

---

## 🔧 下一階段任務優先順序

### ✅ 第一階段（已完成）
| 優先級 | 任務 | 狀態 |
|--------|------|------|
| 🔴 High | 加入 `try/except` 保護與關鍵日誌記錄 | ✅ 已完成並合併 PR |

---

### 🟡 第二階段（已完成）
| 優先級 | 任務 | 說明 |
|--------|------|------|
| 🟡 High | **交易費用設定選項化** | ✅ 已完成：加入 `fee_mode` 設定，支援 taker/maker/mixed 模式。 |
| 🟡 High | **補上 `self.ready_to_trade = True`** | ✅ 已完成：加入 `start()` 確保狀態顯示正常。 |
| 🟡 Medium | **將 `get_most_profitable_combination()` 回傳改為清單** | ✅ 已完成：使用排序回傳多個組合，提升策略靈活性。 |

---

### 🟢 第三階段（架構優化與進階功能）
| 優先級 | 任務 | 說明 |
|--------|------|------|
| 🟢 Medium | **改用雙邊價格平均估算 Position Size** | 避免只依賴 `connector_1` 導致錯誤，改用雙邊 mid price。需調整 `get_position_executors_config()`。 |
| 🟢 Medium | **改善平倉條件設計** | 改用「移動式停利 + 停損」組合邏輯，提升出場決策的彈性與安全性。可參考 `trailing_stop` 演算法設計。 |
| 🟢 Medium | **資金費率歷史預測機制** | 使用過去資金費率計算趨勢線或滑動平均，預測未來 8 小時的趨勢。可簡單先用 EMA。 |
| 🟢 Medium | **風險控管與市場資料驗證強化** | 為每次交易決策前的價格與資金費率資料加入有效性驗證（如過舊、不合理價格排除）。 |

---

### ⚪ 第四階段（細節與風險處理）
| 優先級 | 任務 | 說明 |
|--------|------|------|
| ⚪ Low | **改善型別定義與預設值** | 例如 `token_whitelist` 使用 `Set[str]` 且預設為 `{"WIF", "FET"}`。 |
| ⚪ Low | **變數命名更直觀** | 將 `funding_rate_diff_stop_loss` 改為 `min_funding_rate_diff_to_stop` 等。 |
| ⚪ Low | **處理負的 TP 天數顯示問題** | 避免在 `Days to TP` 顯示負數值，引導使用者做出誤判。 |
| ⚪ Low | **使用者設定值驗證機制** | 為所有 config 欄位加入範圍與合法值檢查，提高使用安全性。 |
| ⚪ Low | **部位大小動態調整** | 根據市場流動性或波動度自動調整單次下單數量，減少風險。 |
| ⚪ Low | **缺乏長期部位再平衡機制** | 若市場價格偏離原始開倉價太多，可考慮重新調整兩邊倉位。 |
