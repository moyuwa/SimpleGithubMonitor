# SimpleGithubMonitor
简单的Github监控程序，部分扩展未实现。可监控多个关键字，有存储记录功能。

使用pyinstaller打包，双击run.bat直接运行exe，win10可免python环境，其他系统需要安装python以及依赖库。

附赠关键字“cve-20”全部github数据库，和已生成win10环境的exe程序（https://github.com/moyuliu/SimpleGithubMonitor/releases/download/1.0/6t-Github-look.exe）。

使用GithubAPI监控关键字

	填写mail.ini配置信息，收件人列表以空格分隔，sleep单位为分钟
	密码/授权码 (部分邮箱需要开启第三方smtp服务，使用授权码登陆)

原理

	使用查询api访问会返回json格式的数据，从中提取出我们需要的数据
	https://api.github.com/search/repositories?q=cve-20&page=1&per_page=1

扩展（未实现功能）

	自动下载高stars项目
	监控和邮件发送分离
	记录上一次脚本启动、数据库更新

已有BUG

	由于网络原因，有时会监控失败
	由于网络原因，有时登陆会失败
	由于未知原因cmd输出有时会卡住（已用bat脚本启动方式修复）

使用

	文件mail.ini中to值以空格分隔
	数据库条数比GitHub结果多，表示有GitHub项目删除了
  	推荐python安装pyinstaller打包成exe，可在同版本系统中免环境运行

