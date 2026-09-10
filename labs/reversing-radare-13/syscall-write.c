#include <sys/sendfile.h>
#include <sys/stat.h>
#include <errno.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <fcntl.h>

void main(){
    int fd = open("foo", O_WRONLY | O_CREAT, 0644);
    write(fd, "hello_world", 11);
    write(1,"hello world", 11);
    close(fd);

    printf("\nhello world2\n");
}
