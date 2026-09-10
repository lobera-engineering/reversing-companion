#include <sys/sendfile.h>
#include <sys/stat.h>
#include <errno.h>
#include <unistd.h>
#include <stdio.h>
#include <fcntl.h>
#include <stdlib.h>

#define BSIZE 16384

void main(){
    int fin, fout;
    char buf[BSIZE];
    int count;

    if ((fin = open("foo", O_RDONLY)) < 0){
        perror("foo");
        exit(2);
    }
    if((fout = open("bar", O_WRONLY | O_CREAT, 0644)) < 0){
        perror("bar");
        exit(2);
    }
    while ((count = read(fin, buf, BSIZE)) > 0)
        write(fout, buf, count);

    close(fin);
    close(fout);
}
