#include <stdio.h>
#include <string.h>
main(){
funcion();
getchar();
}


funcion()
{ 

    FILE* ftest;
    char name[80] = "test.txt";
    char line[81];
 
    ftest = fopen(name, "rt");
 
    if (ftest == NULL)
    {
      printf("file not found!\n");
      exit(1);
    }
    fgets(line, 80, ftest);
    puts(line);
    fgets(line, 80, ftest);
    puts(line);
    fclose(ftest);


}
