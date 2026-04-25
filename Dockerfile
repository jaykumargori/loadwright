FROM alpine:3.22

ARG TARGETPLATFORM

COPY ${TARGETPLATFORM}/loadwright /usr/local/bin/loadwright

WORKDIR /work
USER 10001:10001
ENTRYPOINT ["loadwright"]
CMD ["help"]
