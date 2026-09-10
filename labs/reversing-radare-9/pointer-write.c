#include <stdio.h>
#include <stdlib.h>

int main(){

    int i = 2;

    char c = 'c';

    char* pc = &c;

    printf("Value of i: %d \n",i);
    printf("Address of i: %p \n",&i);
    printf("Value of c: %c \n", c);
    printf("Address of c: %p \n",&c);

    printf("Updating the content of the mem address pointed by pc \n");

    *pc = 'b';

    printf("Value of c: %c \n", c);

return 0;
}
