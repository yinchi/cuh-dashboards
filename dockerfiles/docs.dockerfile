FROM httpd:alpine
COPY docs/ /docs
COPY documentation/httpd.conf /httpd.conf
EXPOSE 8888
CMD ["httpd", "-d", "/docs", "-f", "/httpd.conf", "-D", "FOREGROUND"]
