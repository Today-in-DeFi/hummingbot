# 📦 功能名稱：交易費用設定選項化

## ✅ 任務一：補上 `self.ready_to_trade = True`

### 📌 原因  
`ready_to_trade` 是 Hummingbot 用來顯示策略狀態（例如 UI 中顯示 "Ready"）的旗標，但目前在 `start()` 函數中沒有設置這個欄位，因此會導致 UI 或 CLI 中顯示錯誤。

### 🧩 Diff patch

```diff
@@ def start(self):
     # initialization logic ...
 
+    self.ready_to_trade = True
     self.logger().info("Strategy is ready to trade.")
```

---

## ✅ 任務二：將 `get_most_profitable_combination()` 改為回傳所有符合條件的清單

### 📌 原因  
目前的策略僅挑選「獲利最大」的一對交易所和幣種組合進行套利，但這會錯過一些其他同樣超過門檻、可並行操作的套利機會。改為回傳排序後的清單，可以讓策略：
- 並行開多筆套利倉位（若未來支援）
- 讓使用者設定偏好排序條件
- 更靈活決策而非硬性只選一組

### 🧩 Diff patch

```diff
@@ def get_most_profitable_combination(self) -> Optional[Tuple[str, str, TradeType, Decimal]]:
-    best_combination = None
-    best_profitability = Decimal("-inf")
+    profitable_combinations = []

     for token in self.config.token_whitelist:
         for conn_1 in self.config.exchanges:
             for conn_2 in self.config.exchanges:
                 if conn_1 == conn_2:
                     continue
                 for side in [TradeType.BUY, TradeType.SELL]:
                     try:
                         profitability = await self.get_current_profitability_after_fees(
                             token, conn_1, conn_2, side
                         )
-                        if profitability > best_profitability and profitability > self.config.min_profitability:
-                            best_combination = (token, conn_1, conn_2, side, profitability)
-                            best_profitability = profitability
+                        if profitability > self.config.min_profitability:
+                            profitable_combinations.append(
+                                (token, conn_1, conn_2, side, profitability)
+                            )
                     except Exception as e:
                         self.logger().warning(f"Error evaluating {token} on {conn_1}/{conn_2}: {e}")
 
-    return best_combination
+    # sort by profitability descending
+    profitable_combinations.sort(key=lambda x: x[4], reverse=True)
+    return profitable_combinations
```

### 📌 注意事項
- 上述改法會讓 `get_most_profitable_combination()` 回傳一個清單（`List[Tuple[...]]`）
- 呼叫這個函式的地方也要一起修改，例如只取最好的組合 `result[0]` 或遍歷整個清單

如果你想我幫你同時調整呼叫端的邏輯，我可以補上這段（建議你先確認是否支援多倉或是否只保留一組）。

---

需要我幫你把這兩項改動包成完整 patch 或整合成 commit message 嗎？還是你要先實作？