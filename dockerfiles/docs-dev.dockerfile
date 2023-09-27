FROM httpd:alpine
COPY documentation/httpd.conf /httpd.conf
EXPOSE 8888
CMD ["httpd", "-d", "/docs", "-f", "/httpd.conf", "-D", "FOREGROUND"]
