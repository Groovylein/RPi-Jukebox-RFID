FROM hvalev/spotifyd-pulseaudio

ARG UID
ARG USER
ARG HOME

USER root
RUN test ${UID} -gt 0 && useradd -m -u ${UID} ${USER} || continue
RUN usermod -aG pulse ${USER}
