#include <stdio.h>
#include <string.h>
#include <stdlib.h>

void greet_me(){

        char name[200];
        gets(name);
        printf("hi there %s !!\n",name);
}

int main(int argc, char *argv[]){

        greet_me();

        return 0;

}
