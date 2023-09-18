FROM httpd:alpine
COPY docs/build/html /docs
COPY docs/httpd.conf /httpd.conf
EXPOSE 8888
CMD ["httpd", "-d", "/docs", "-f", "/httpd.conf", "-D", "FOREGROUND"]
