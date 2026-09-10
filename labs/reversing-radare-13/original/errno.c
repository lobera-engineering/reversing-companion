#include <fcntl.h>
#include <stdio.h>

void main(){
    fd = open("foo", O_WRONLY | O_CREAT, 0644);
    if(fd >= 0){
        write(fd, "hello_world", 11);
        close(fd);
    }
    else{
        printf("error number %d\n", errno);
        perror("foo");
        exit(1);
    }
}
