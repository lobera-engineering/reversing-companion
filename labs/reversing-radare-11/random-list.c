#include <stdio.h>
#include <time.h>
#include <stdlib.h>

int randy(){
	int r = rand(); 

	return r % 20 + 5;

}

struct node {
  int i;
  struct node *next;
};


int main(){
	srand(time(NULL));   // Initialization, should only be called once.
	int ran = 0;

	struct node *ant; 
	struct node *first_node = NULL;

	first_node = malloc(sizeof(struct node));

	first_node->i = 1;
	ant = first_node;


	for(int i = 0; i < randy(); i++){

		struct node *actual;
		actual =  malloc(sizeof(struct node));
		actual->next = NULL;
		actual->i = randy();

		ant->next = actual;
		ant = actual;

	}

	return 0;
}
