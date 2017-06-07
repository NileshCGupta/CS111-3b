.SILENT:
subfiles = lab3b.py Makefile README

default:
	cp lab3b.py lab3b
	chmod +x lab3b
dist:
	tar -zcvf lab3b-604-489-201.tar.gz $(subfiles)
clean:
	rm lab3b *.tar.gz