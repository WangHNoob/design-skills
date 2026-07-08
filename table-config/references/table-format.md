# gamedata 配表格式参考

配表的权威格式来源是 gamedata 目录下的真实 `.xlsx` 文件（`<知识库根>/gamedata`，由环境变量 `TABLE_CONFIG_GAMEDATA` 指定；首选走 MCP `kb_get_table_raw`，无需本地文件）。
`kb_query_table` 的 JSON 会丢列序和空列身份（出现 `__EMPTY`），**只用来学值、不用来定格式**。

## 表头结构：行数与顺序因表而异

不能假设固定表头。用 `table_tool.py read --fields <schema字段>` 让脚本**自动定位**字段名行与数据起始行。
三个真实例子（说明差异有多大）：

**_AchievementLevel**（3 行表头）
```
行0: 中文说明   成就点数 / (空) / 成就级别 / 成就奖励
行1: 字段名     point / (空) / level / reward
行2: 类型       int / (空) / int / string
行3+: 数据
```

**_AccumulativePay**（表头到第 5 行，字段名行出现两次）
```
行0: 列ID       7, 1, 9999, 4
行1: 中文说明   id, 档位, 需要累计彩钻, 奖励
行2: 字段名     id, stallId, needDiamond, rewards
行3: 类型       int, int, int, string
行4: 约束       primary, none, none, none
行5: 字段名(重复) id, stallId, needDiamond, rewards
行6+: 数据       1, 1, 1000, "1200,460009,1;1001,212002,10;..."
```

**_AchievementCondition**（表头到第 4 行）
```
行0: 列ID       1, 6, 7, 9999, __EMPTY, __EMPTY_1   ← JSON 里丢了标识；真实 xlsx 里是完整列
行1: 中文说明   成就id, 目标值, 成就条件id, 条件类型, 扩展值, 成就条件描述
行2: 字段名     achievementId, target, id, type, external, description
行3: 类型       int, int, int, int, string, string
行4: 约束       index, none, primary, none, none, none
行5+: 数据
```

## 关键约定

- **列 ID（第 0 行）**：如 `7,1,9999,4`。是稳定的列标识（多为客户端/服务端可见性或导出标记），`9999` 常是约定标记列。**生成时原样保留**——脚本复制整个表头块即可，无需你手动处理。
- **约束行**：`primary`（主键，须唯一非空）、`index`（索引）、`none`。校验主键唯一性时看这一行。
- **字段名可能重复出现两次**（如 AccumulativePay 的行2、行5）。脚本取**最后一个**字段名行作为数据前的锚点，照抄前面所有行。

## 编码小语言（生成值前必须先学）

配表里很多字段不是单值，而是编码串。**别自造，先从同表已有数据 `kb_query_table` 学**。

**奖励类（rewards）**：分号分隔多组，每组 `类型,道具ID,数量`
```
1200,460009,1;1001,212002,10;1001,452201,10;5,0,50000
└─ 一组：type=1200, itemId=460009, count=1
```
- 生成奖励时，每个 `道具ID` 都要用 `kb_check_table_value` / `kb_query_table` 验证在对应道具/资源表里真实存在。
- `类型` 段的含义（如 1001/1200/5 分别代表什么）从同类表或知识库页面查证，不要臆测。

**条件类（如 AchievementCondition 的 type/target/external）**：
- `type` 是条件类型枚举，`target` 是目标值，`external` 是扩展参数。取值范围从同表已有行归纳。

## 校验要点

1. **字段齐全**：数据行覆盖 schema 所有必填字段（`kb_get_table_schema` 的 fields）。
2. **主键唯一非空**：约束行标 `primary` 的列，值不重复、不为空（`table_tool.py validate` 自动查）。
3. **类型匹配**：int 列填整数、string 列填字符串。
4. **外键/引用存在**：编码串里引用的道具ID、表项，用 `kb_check_table_value` 验证目标存在（脚本不做，skill 负责）。
5. **取值范围**：对照同表已有数据的范围，异常值要么有依据、要么标「待确认」。
