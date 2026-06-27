DROP TABLE IF EXISTS t_rate;

CREATE TABLE t_rate (
    Method       VARCHAR(60) NOT NULL COMMENT '方法 快加 快刷(极速) 凑卡(网单 ，快速网单) 括号内为 别名 只针对于苹果卡  其他所有卡默认为快刷 注意 苹果卡 50面值 只有快加和快刷',
    CardName     VARCHAR(60) NOT NULL COMMENT '卡名',
    value        VARCHAR(40) NOT NULL COMMENT '面值范围',
    rate         VARCHAR(60) NOT NULL COMMENT '汇率',
    Exolanation  VARCHAR(80) NOT NULL COMMENT '说明 只能为区间匹配和精准匹配以及区间匹配',
    Region       VARCHAR(60) NOT NULL COMMENT '地区国家',
    GroupName    VARCHAR(60) COMMENT '群名称',
    btime        DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据被更新到表的时间'
) COMMENT = '表t_rate为汇率表，用于存放所有汇率包含所有方法（快加 快刷 凑卡 ）';




