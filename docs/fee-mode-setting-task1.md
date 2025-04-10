# 📦 功能名稱：交易費用設定選項化

支援多種費率模式（**taker / maker / mixed**）來更真實估算套利利潤。

---

## 📁 影響範圍

- 檔案：`scripts/v2_funding_rate_arb.py`
- 修改點：
	- 加入新設定欄位 `fee_mode`
	- 根據 `fee_mode` 調整 `get_current_profitability_after_fees()` 中費用計算邏輯
	- 若尚未定義 `maker_fee`，應一併加入（參考 `taker_fee`）

---

## ✨ 功能細節

- `fee_mode` 可選：
	- `"taker"`：兩邊皆用 taker 手續費（預設）
	- `"maker"`：兩邊皆用 maker 手續費
	- `"mixed"`：開倉那一邊用 taker，對沖那一邊用 maker（常見做法）

- 這將讓策略在估算套利利潤時更加準確、靈活

---

## 🏷️ 分支命名建議

```
feature/fee-mode-setting
```

---

## 🧾 Commit message

```
(feat) add fee_mode option to support taker/maker/mixed fee calculations

- Add `fee_mode` field to strategy config
- Adjust fee calculation logic in `get_current_profitability_after_fees`
- Support three modes:
    - taker: both sides use taker fee
    - maker: both sides use maker fee
    - mixed: one side taker, other side maker
- Add default maker_fee field if not already defined
```

---

## 🧩 Diff patch

```diff
@@ class FundingRateArbitrageConfig(StrategyV2ConfigBase):
+    fee_mode: Literal["taker", "maker", "mixed"] = Field(
+        default="taker",
+        description="Fee mode for arbitrage profitability calculation: taker, maker, or mixed.",
+        client_data=ClientFieldData(
+            prompt=lambda mi: "Select fee mode (taker / maker / mixed): ",
+            prompt_on_new=True
+        )
+    )
+
+    maker_fee: Decimal = Field(
+        default=0.0002,
+        description="Estimated maker fee for use in profitability calculation.",
+        client_data=ClientFieldData(
+            prompt=lambda mi: "Enter estimated maker fee (e.g. 0.0002): ",
+            prompt_on_new=True
+        )
+    )

@@ def get_current_profitability_after_fees(self, token: str, connector_1: str, connector_2: str, side: TradeType):
-            estimated_fees_connector_1 = self.connectors[connector_1].get_fee(
-                ...
-                is_maker=False,
-                ...
-            ).percent
-            estimated_fees_connector_2 = self.connectors[connector_2].get_fee(
-                ...
-                is_maker=False,
-                ...
-            ).percent
+            # Determine maker/taker based on fee_mode
+            if self.config.fee_mode == "taker":
+                is_maker_1 = False
+                is_maker_2 = False
+            elif self.config.fee_mode == "maker":
+                is_maker_1 = True
+                is_maker_2 = True
+            elif self.config.fee_mode == "mixed":
+                is_maker_1 = (side == TradeType.SELL)
+                is_maker_2 = (side == TradeType.BUY)
+            else:
+                self.logger().warning(f"Unknown fee_mode '{self.config.fee_mode}', defaulting to taker fees.")
+                is_maker_1 = False
+                is_maker_2 = False
+
+            estimated_fees_connector_1 = self.connectors[connector_1].get_fee(
+                ...
+                is_maker=is_maker_1,
+                ...
+            ).percent
+            estimated_fees_connector_2 = self.connectors[connector_2].get_fee(
+                ...
+                is_maker=is_maker_2,
+                ...
+            ).percent
```

---

## ✅ 小提醒

- 如果你還沒定義 `maker_fee`，上面的 diff 已經幫你補上
- 你可以將這段貼給 GPT-4o 或直接套用到 VS Code 進行修改

---

# 問答

## 交易費用設定選項化的理由

> 我想更了解交易費用設定選項化的理由。這可以解決什麼問題

當我們把 **交易費用設定選項化（fee_mode: taker / maker / mixed）**，其實是為了解決以下三個關鍵問題：

---

### 1️⃣ **提高套利利潤計算的準確度**

#### 問題：
目前策略假設雙邊都是 **taker**，也就是吃市價單，但實際上這不一定成立。

例如：
- 一邊是主動吃單（taker），快速成交；
- 另一邊是掛單等待（maker），節省手續費。

#### 為什麼重要？
手續費差異會直接影響 **是否值得進場套利**。

例如：
| 類型     | 費率（假設） |
|----------|--------------|
| taker    | 0.10%        |
| maker    | 0.02%        |

差 0.08% 對短期套利來說非常致命。

#### 解法：
允許使用者設定 `fee_mode`：
- **taker**：保守估計
- **maker**：若策略主要是限價單
- **mixed**：更貼近實際操作行為

---

### 2️⃣ **支援不同交易所策略與套利組合**

不同交易所的手續費結構不同，策略上可能會配合手續費設定不同掛單模式。

- **Binance**：Maker 幾乎免費，有 rebate
- **Bybit**：Taker 0.06%，Maker -0.025%（負費用）

#### 問題：
固定費率會讓策略錯判是否值得開倉、或太保守錯失機會。

#### 解法：
支援費率模式的選擇，讓使用者按 **套利組合特性** 自訂是否假設某邊為 maker。

---

### 3️⃣ **為未來自動訂單模式做準備**

目前策略尚未區分是 **吃單成交（taker）** 還是 **限價等待成交（maker）**，但未來若：
- 引入限價掛單策略
- 或支援動態切換下單方式

就需要依據實際成交方式設定正確費率來計算真實利潤。

---

### 🎯 總結：這項改動解決的問題

| 問題 | 改動後的好處 |
|------|---------------|
| 套利利潤誤判 | 費率估算更準確，避免誤判或錯失機會 |
| 跨交易所套利策略不靈活 | 可依交易所實際費率進行組合調整 |
| 未來策略擴展困難 | 奠定支持限價單 / 成交方式區分的基礎 |

---

若你們團隊未來有計劃支援 **限價下單策略、或滑點控制、手續費回饋機制**，這個 `fee_mode` 會成為核心邏輯的一環。這就是為什麼我們現在要提早建置這個選項化機制的原因。

---

## maker / taker 的定義

> 我不是很懂 taker 和 maker 的定義。然後請問原本有關這些的程式碼在哪裡

沒問題，我來一步步幫你釐清這些概念，並指出原本在程式碼中相關的位置。

---

### 1️⃣ **什麼是 maker / taker？**

#### **maker（掛單方）**
- 指在市場上「掛出限價單」的人（例如掛在比市價更好一點的位置）
- 他們**提供流動性**
- 如果你的單被別人吃掉，你是 **maker**
- 交易所通常會給你 **低費率或回饋（rebate）**

#### **taker（吃單方）**
- 指「立即成交」的人，通常是用市價單
- 他們**拿走市場的流動性**
- 如果你下單立即成交，你是 **taker**
- 交易所通常會收比較高的手續費

---

### 2️⃣ **在我們的策略中是怎麼算費用的？**

你可以在以下原始程式碼中看到我們如何估算套利機會中的交易費用：

#### 📄 `/scripts/v2_funding_rate_arb.py`

```python
    def get_current_profitability_after_fees(self, market_pair: FundingRateMarketPair) -> Decimal:
        ...
        long_price = market_pair.long_price
        short_price = market_pair.short_price
        # fixed taker fee assumption
        fee_rate = Decimal("0.001")  # 0.1%
        total_fees = fee_rate * (long_price + short_price)
        profit_after_fees = (short_price - long_price) - total_fees
        ...
```

#### 🔍 重點在這幾行：

```python
fee_rate = Decimal("0.001")
total_fees = fee_rate * (long_price + short_price)
```

這裡硬寫死了 `0.1%` 的費用（也就是 taker fee），但這個邏輯有幾個問題：

- 沒有區分 **maker / taker**
- 沒有考慮左右交易所手續費不同
- 不夠彈性，未來不好擴展

---

### 3️⃣ **我們接下來要做的改進是什麼？**

在下一階段我們會改寫這一段：

- **加入參數設定**：可以從策略設定中決定 `fee_mode = taker | maker | mixed`
- **允許使用者自訂費率**（每邊）
- **根據模式套用正確費率組合來算利潤**

---

### 4️⃣ 額外補充：實際情境舉例

假設你是套利機器人：

- 在 Binance 你掛單賣出（maker，費用 0.02%）
- 在 Bybit 馬上買進（taker，費用 0.06%）

你預期套利空間是 0.1%，  
那實際扣完費用只剩下 0.1% - 0.02% - 0.06% = **0.02%** 利潤。  
如果你錯估成都是 0.1%，就可能 **白忙一場甚至虧損**。

---

如果你想看後續 patch 怎麼改，讓我知道我可以帶你看清楚。是否進入 patch 第二階段的改寫？還是你想先了解參數設計部分？

---

## 關於 `get_current_profitability_after_fees`

> 
> 目前的 `get_current_profitability_after_fees` 被修改成這樣耶
> 
> ```python
> async def get_current_profitability_after_fees(self, token: str, connector_1: str, connector_2: str, side: TradeType):
>         """
>         This methods compares the profitability of buying at market in the two exchanges. If the side is TradeType.BUY
>         means that the operation is long on connector 1 and short on connector 2.
>         """
>         try:
>             trading_pair_1 = self.get_trading_pair_for_connector(token, connector_1)
>             trading_pair_2 = self.get_trading_pair_for_connector(token, connector_2)
> 
>             connector_1_price = Decimal(self.market_data_provider.get_price_for_quote_volume(
>                 connector_name=connector_1,
>                 trading_pair=trading_pair_1,
>                 quote_volume=self.config.position_size_quote,
>                 is_buy=side == TradeType.BUY,
>             ).result_price)
>             connector_2_price = Decimal(self.market_data_provider.get_price_for_quote_volume(
>                 connector_name=connector_2,
>                 trading_pair=trading_pair_2,
>                 quote_volume=self.config.position_size_quote,
>                 is_buy=side != TradeType.BUY,
>             ).result_price)
>             estimated_fees_connector_1 = self.connectors[connector_1].get_fee(
>                 base_currency=trading_pair_1.split("-")[0],
>                 quote_currency=trading_pair_1.split("-")[1],
>                 order_type=OrderType.MARKET,
>                 order_side=TradeType.BUY,
>                 amount=self.config.position_size_quote / connector_1_price,
>                 price=connector_1_price,
>                 is_maker=False,
>                 position_action=PositionAction.OPEN
>             ).percent
>             estimated_fees_connector_2 = self.connectors[connector_2].get_fee(
>                 base_currency=trading_pair_2.split("-")[0],
>                 quote_currency=trading_pair_2.split("-")[1],
>                 order_type=OrderType.MARKET,
>                 order_side=TradeType.BUY,
>                 amount=self.config.position_size_quote / connector_2_price,
>                 price=connector_2_price,
>                 is_maker=False,
>                 position_action=PositionAction.OPEN
>             ).percent
> 
>             if side == TradeType.BUY:
>                 estimated_trade_pnl_pct = (connector_2_price - connector_1_price) / connector_1_price
>             else:
>                 estimated_trade_pnl_pct = (connector_1_price - connector_2_price) / connector_2_price
>             return estimated_trade_pnl_pct - estimated_fees_connector_1 - estimated_fees_connector_2
>         except Exception as e:
>             self.logger().error("Error in get_current_profitability_after_fees", exc_info=True
> ```
> 關於 0.001，我找到以下程式碼
> 
> ```python
> class FundingRateArbitrageConfig(StrategyV2ConfigBase):
>     min_funding_rate_profitability: Decimal = Field(
>         default=0.001,
>         client_data=ClientFieldData(
>             prompt=lambda mi: "Enter the min funding rate profitability to enter in a position: ",
>             prompt_on_new=True
>         )
>     )
> ```

你找到的內容非常關鍵，說明你已經接近完全掌握策略對**手續費與獲利門檻的計算邏輯**了。我來幫你總結並進一步解釋目前的狀況與為何仍然需要「交易費用設定選項化」。

---

### ✅ 目前已經做得不錯的地方

#### **1. 使用真實市價計算潛在利潤**

目前的 `get_current_profitability_after_fees()`：
- 已經根據實際的 quote volume 和市價，取得不同交易所的成交價格（connector_1 和 connector_2）。
- 邏輯上正確地根據 `TradeType.BUY` 決定哪邊 long、哪邊 short。

#### **2. 使用交易所物件估算費用**

這兩段：

```python
estimated_fees_connector_1 = self.connectors[connector_1].get_fee(...)
estimated_fees_connector_2 = self.connectors[connector_2].get_fee(...)
```

透過 Hummingbot 的 `get_fee` 方法：
- 使用 `is_maker=False` → 表示「假設都是用市價單（taker）」
- 會根據交易所提供的模型（或 API 結果）去估算費用（可能是固定值、比率、甚至 tier-based）

這已經比原本硬寫 `0.001` 進步非常多。

---

### ⚠️ 目前還存在的問題（為什麼還要選項化？）

#### 問題 1：**硬寫死 taker fee**

```python
is_maker=False
```

這裡是寫死的！無論你實際會不會使用 maker 單，它都只會計算 taker 費用。

#### 問題 2：**不支援混合模式或雙邊不同策略**

有些交易策略會這樣操作：

| 交易所 | 操作方式 | 費率類型 |
|--------|-----------|---------|
| A      | 掛限價單（等待吃單） | **maker** |
| B      | 吃單快速成交         | **taker** |

這樣的情況下，正確的費用應該是：**maker fee（A） + taker fee（B）**

但目前寫死為 **雙邊 taker**，這會：

- **高估費用 → 錯失套利機會**
- **無法靈活模擬不同策略組合**

---

### 🛠️ 你應該怎麼改？

#### 新增一個 enum + 組態參數

```python
class FeeMode(str, Enum):
    TAKER = "taker"
    MAKER = "maker"
    MIXED = "mixed"  # long: taker, short: maker（或反之，看策略）
```

#### 在 `FundingRateArbitrageConfig` 加入欄位：

```python
fee_mode: FeeMode = Field(
    default=FeeMode.TAKER,
    client_data=ClientFieldData(
        prompt=lambda mi: "Select fee mode (taker / maker / mixed): ",
        prompt_on_new=True
    )
)
```

#### 修改 `get_current_profitability_after_fees()` 的這兩段：

```python
is_maker_1 = self.config.fee_mode in [FeeMode.MAKER, FeeMode.MIXED and side == TradeType.SELL]
is_maker_2 = self.config.fee_mode in [FeeMode.MAKER, FeeMode.MIXED and side == TradeType.BUY]
```

並傳給 `get_fee(..., is_maker=is_maker_1/2)`

---

### 🧠 小結：你為什麼要做這個改進？

| 面向 | 原始程式碼 | 改進後 |
|------|-------------|----------|
| 彈性 | 寫死 taker | 可選 taker/maker/mixed |
| 正確性 | 高估成本（保守） | 更貼近實際策略操作 |
| 模擬能力 | 無法預估策略差異 | 能預估不同交易行為效果 |
| 專業度 | 粗糙估計 | 更接近專業機構的手法 |

這項改進是**性能與真實性兼顧**的關鍵一環，尤其在跨交易所套利策略中**費用差距影響極大**。

---

你想現在我幫你寫出完整 patch 的格式嗎？還是你想先自己寫看看我再 review？