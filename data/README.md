# 数据目录

此目录用于存放基金分析工具生成的本地数据文件，包括：

- **CSV 文件**: 通过 `reporter.export_to_csv()` 导出的基金净值数据
- **Markdown 报告**: 通过 `reporter.generate_report()` 生成的分析报告
- **缓存数据**: `fetcher` 模块自动缓存的数据文件，避免重复请求

## 目录结构建议

```
data/
├── csv/            # 导出的净值CSV文件
├── reports/        # 生成的Markdown报告
└── cache/          # 自动缓存 (由 fetcher 管理)
```

> 注意: cache 目录下的文件由程序自动管理，请勿手动修改。
